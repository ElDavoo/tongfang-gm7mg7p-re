using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Forms;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Microsoft.Win32;
using MyECIO;
using Newtonsoft.Json;
using RegistryUtils;
using Utility;

namespace MyControlCenter;

public class OSDManager
{
	private string m_className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	public uint g_osd_switch = 1u;

	private string m_sLang = "en-us";

	private static RegistryMonitor m_registryMonitor;

	private string m_sRegPath = "\\OEM\\GamingCenter2";

	private double _TriggerParam = 1.0;

	private double _UnTriggerParam = 0.3;

	private Color _OSDDefaultColor = Color.FromArgb(byte.MaxValue, 0, 0, 0);

	private bool _OSDSystemHidden = true;

	private HiddenOSDLib hiddenOSDLib;

	private int m_ProjectID;

	private int m_nCustomizeTarget = 1;

	private int m_nBridgeType;

	private int m_nOsdWidth = -1;

	private List<ushort> FullScreenDontSowOSDList = new List<ushort> { 2, 1 };

	public void EnableByService()
	{
		LogCtrl.Write(m_className + "[EnableByService] GetCurrentOSDColor");
		_OSDDefaultColor = GetCurrentOSDColor();
		m_ProjectID = EcCtrl.GetProjectIdFromEC();
		m_nCustomizeTarget = RegistryCtrl.GetCustomizeTarget();
		m_nBridgeType = RegistryCtrl.GetBridgeType();
		_ = m_nCustomizeTarget;
		m_nOsdWidth = -1;
		CreateTpDetect.Start();
		CreateIDMTpDetect.Start();
	}

	public async void Recieve(byte[] data)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data));
		string text = val["Action"];
		_ = string.Empty;
		LogCtrl.TraceMessage("---------------" + LogCtrl.GetTime() + "---------------", "Recieve", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\OSD\\OSDManager.cs", 170);
		LogCtrl.TraceMessage("msg = " + text, "Recieve", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\OSD\\OSDManager.cs", 171);
		if (!(text == "GET"))
		{
			if (text == "SET")
			{
				string lang = val["Lang"];
				SetLang(lang);
			}
		}
		else
		{
			GetLang();
		}
	}

	private void GetLang()
	{
		string languageList = "en-us";
		string language = "en-us";
		try
		{
			languageList = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "LanguageList", "en-us");
			language = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "Language", "en-us");
		}
		catch
		{
		}
		var data = new
		{
			LanguageList = languageList,
			Language = language
		};
		App.m_MQTTService.Publish("Languages/Info", data, retain: false);
		string oSDTpString = GetOSDTpString();
		App.m_MQTTService.Publish_ByUTF8("OSDTpDectect/Language", new
		{
			OSDTpString = oSDTpString
		}, retain: false);
	}

	private void SetLang(string sLang)
	{
		try
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath, "Language", sLang, RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\TpDetect", "Language", sLang, RegistryValueKind.String);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage($"RegistrySoftwareKeyWrite Failed {ex.ToString()}", "SetLang", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\OSD\\OSDManager.cs", 219);
		}
		OSDChangeSizeByLanguage(sLang);
		string oSDTpString = GetOSDTpString();
		App.m_MQTTService.Publish_ByUTF8("OSDTpDectect/Language", new
		{
			OSDTpString = oSDTpString
		}, retain: false);
	}

	private void OSDChangeSizeByLanguage(string Language)
	{
		if (Language == "ru-ru")
		{
			if (m_nCustomizeTarget == 41)
			{
				m_nOsdWidth = 550;
			}
			else
			{
				m_nOsdWidth = -1;
			}
		}
		else
		{
			m_nOsdWidth = -1;
		}
	}

	private Color GetCurrentOSDColor()
	{
		string colorcode = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath + "\\MySetting\\", "OSDColor", "#FF000000");
		return ConvetToMediaColor(colorcode);
	}

	private bool GetCurrentOSDSystemHidden()
	{
		if ((int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath + "\\MySetting\\", "OSDSystemHidden", 1) != 0)
		{
			return true;
		}
		return false;
	}

	private Color ConvetToMediaColor(string colorcode)
	{
		colorcode = colorcode.TrimStart('#');
		if (colorcode.Length == 6)
		{
			return Color.FromArgb(byte.MaxValue, (byte)int.Parse(colorcode.Substring(0, 2), NumberStyles.HexNumber), (byte)int.Parse(colorcode.Substring(2, 2), NumberStyles.HexNumber), (byte)int.Parse(colorcode.Substring(4, 2), NumberStyles.HexNumber));
		}
		return Color.FromArgb((byte)int.Parse(colorcode.Substring(0, 2), NumberStyles.HexNumber), (byte)int.Parse(colorcode.Substring(2, 2), NumberStyles.HexNumber), (byte)int.Parse(colorcode.Substring(4, 2), NumberStyles.HexNumber), (byte)int.Parse(colorcode.Substring(6, 2), NumberStyles.HexNumber));
	}

	private ResourceDictionary SetResourceDictionary()
	{
		try
		{
			m_sLang = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "Language", "en-us");
		}
		catch
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath, "Language", m_sLang, RegistryValueKind.String);
		}
		OSDChangeSizeByLanguage(m_sLang);
		ResourceDictionary resourceDictionary = new ResourceDictionary();
		switch (m_sLang)
		{
		case "en-us":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\en-US.xaml", UriKind.Relative);
			break;
		case "zh-cn":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\zh-CN.xaml", UriKind.Relative);
			break;
		case "tr-tr":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\tr-Tr.xaml", UriKind.Relative);
			break;
		case "zh-tw":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\zh-TW.xaml", UriKind.Relative);
			break;
		case "de-de":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\de-DE.xaml", UriKind.Relative);
			break;
		case "hu-hu":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\hu-HU.xaml", UriKind.Relative);
			break;
		case "ko-kr":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\ko-KR.xaml", UriKind.Relative);
			break;
		case "ru-ru":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\ru-RU.xaml", UriKind.Relative);
			break;
		case "ja-jp":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\ja-JP.xaml", UriKind.Relative);
			break;
		case "pl-pl":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\pl-PL.xaml", UriKind.Relative);
			break;
		case "es-es":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\es-ES.xaml", UriKind.Relative);
			break;
		case "fr-fr":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\fr-FR.xaml", UriKind.Relative);
			break;
		case "pt-br":
			resourceDictionary.Source = new Uri("..\\osd\\Language\\pt-BR.xaml", UriKind.Relative);
			break;
		default:
			resourceDictionary.Source = new Uri("..\\Tray\\Language\\en-US.xaml", UriKind.Relative);
			break;
		}
		Task<object> task = ReflashUIString(resourceDictionary);
		foreach (object key in resourceDictionary.Keys)
		{
			if (((dynamic)task.Result)?[key] != null)
			{
				resourceDictionary[key] = (object)((dynamic)task.Result)[key];
			}
		}
		return resourceDictionary;
	}

	private async Task<dynamic> ReflashUIString(ResourceDictionary dict)
	{
		string sLang = m_sLang;
		object fileResource = null;
		try
		{
			fileResource = await LoadLanguageResourceFromPath<object>(sLang, Assembly.GetExecutingAssembly());
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"OSD | ReflashUIString | LoadLanguageResourceFromPath Failed {ex.ToString()}");
		}
		return fileResource;
	}

	private static async Task<T> LoadLanguageResourceFromPath<T>(string language, Assembly assembly)
	{
		string path = string.Concat(LogCtrl.GetParentDirectoryPath(System.Windows.Forms.Application.StartupPath, 2) + "\\logo", "\\Language\\", language, ".json");
		if (File.Exists(path))
		{
			return JsonConvert.DeserializeObject<T>(File.ReadAllText(path));
		}
		return default(T);
	}

	public void DisableByService()
	{
		g_osd_switch = 0u;
		CreateTpDetect.End();
		CreateIDMTpDetect.End();
	}

	public void SetOSDSwitch(int status)
	{
		if (status == 1)
		{
			g_osd_switch = 1u;
			CreateTpDetect.Start();
			CreateIDMTpDetect.Start();
		}
		else
		{
			g_osd_switch = 0u;
			CreateTpDetect.End();
			CreateIDMTpDetect.End();
		}
	}

	public void SetPanelStatus()
	{
		Win32.DISPLAY_DEVICE lpDisplayDevice = default(Win32.DISPLAY_DEVICE);
		lpDisplayDevice.cb = Marshal.SizeOf(lpDisplayDevice);
		try
		{
			for (uint num = 0u; Win32.EnumDisplayDevices(null, num, ref lpDisplayDevice, 0u); num++)
			{
				if ((lpDisplayDevice.StateFlags & 1) != 1)
				{
					continue;
				}
				Console.WriteLine("{0}, {1}", lpDisplayDevice.DeviceName, lpDisplayDevice.StateFlags);
				Win32.DISPLAY_DEVICE lpDisplayDevice2 = default(Win32.DISPLAY_DEVICE);
				lpDisplayDevice2.cb = Marshal.SizeOf(lpDisplayDevice2);
				for (uint num2 = 0u; Win32.EnumDisplayDevices(lpDisplayDevice.DeviceName, num2, ref lpDisplayDevice2, 1u); num2++)
				{
					if ((lpDisplayDevice2.StateFlags & 1) != 1)
					{
						continue;
					}
					Console.WriteLine("{0}, {1}", lpDisplayDevice2.DeviceName, lpDisplayDevice2.StateFlags);
					IntPtr intPtr = Win32.CreateFile(lpDisplayDevice2.DeviceID, 3221225472u, 1u, IntPtr.Zero, 3u, 0u, IntPtr.Zero);
					if (intPtr != IntPtr.Zero)
					{
						bool state = false;
						Win32.GetDevicePowerState(intPtr, out state);
						if (state)
						{
							Win32.SendMessage(-1, 274, 61808, 2);
						}
						else
						{
							Win32.mouse_event(1, 0, 1, 0, 0);
							Thread.Sleep(40);
							Win32.mouse_event(1, 0, -1, 0, 0);
						}
						Win32.CloseHandle(intPtr);
					}
				}
			}
		}
		catch (Exception ex)
		{
			Console.WriteLine($"{ex.ToString()}");
		}
	}

	public void ShowOSD(int scancode, bool airplaneOnOff = false)
	{
		if (g_osd_switch != 0 && (!ScreenDetection.AreApplicationFullScreen() || !FullScreenDontSowOSDList.Contains(Convert.ToUInt16(scancode))))
		{
			bool flag = false;
			string text = "OSD_Universal/";
			string _osdString1 = "";
			string _osdString2 = "";
			double _osdOpacity1 = 0.0;
			double _osdOpacity2 = 0.0;
			ResourceDictionary resourceDictionary = SetResourceDictionary();
			string img_name;
			switch (scancode)
			{
			default:
				return;
			case 167:
			{
				byte Data = 0;
				EcCtrl.Read(GetType().Name, 1873, ref Data);
				ulong num = Convert.ToUInt64(Data);
				img_name = (((num & 0x40) == 64) ? (text + "Performance.png") : (text + "Performance.png"));
				_osdString2 = (((num & 0x40) != 64) ? resourceDictionary["strFanBoostOff"]?.ToString() : resourceDictionary["strFanBoostOn"]?.ToString());
				_osdOpacity2 = 1.0;
				break;
			}
			case 1:
				flag = (Win32.GetKeyState(20) & 1) == 1;
				img_name = (flag ? (text + "Caps on.png") : (text + "Caps off.png"));
				_osdString1 = resourceDictionary["strCapsLock"]?.ToString();
				_osdString2 = resourceDictionary["strCapsUnLock"]?.ToString();
				_osdOpacity1 = (flag ? _TriggerParam : _UnTriggerParam);
				_osdOpacity2 = (flag ? _UnTriggerParam : _TriggerParam);
				break;
			case 2:
				flag = (Win32.GetKeyState(144) & 1) == 1;
				img_name = (flag ? (text + "Num on.png") : (text + "Num off.png"));
				_osdString1 = resourceDictionary["strNumLock"]?.ToString();
				_osdString2 = resourceDictionary["strNumUnLock"]?.ToString();
				_osdOpacity1 = (flag ? _TriggerParam : _UnTriggerParam);
				_osdOpacity2 = (flag ? _UnTriggerParam : _TriggerParam);
				break;
			case 3:
				flag = (Win32.GetKeyState(145) & 1) == 1;
				img_name = (flag ? (text + "Scroll on.png") : (text + "Scroll off.png"));
				_osdString1 = resourceDictionary["strScrollLock"]?.ToString();
				_osdString2 = resourceDictionary["strScrollUnLock"]?.ToString();
				_osdOpacity1 = (flag ? _TriggerParam : _UnTriggerParam);
				_osdOpacity2 = (flag ? _UnTriggerParam : _TriggerParam);
				break;
			case 64:
				img_name = text + "Lock on.png";
				_osdString1 = resourceDictionary["strWinLock"]?.ToString();
				_osdString2 = resourceDictionary["strWinUnLock"]?.ToString();
				_osdOpacity1 = (flag ? _UnTriggerParam : _TriggerParam);
				_osdOpacity2 = (flag ? _TriggerParam : _UnTriggerParam);
				break;
			case 65:
				img_name = text + "Lock off.png";
				_osdString1 = resourceDictionary["strWinLock"]?.ToString();
				_osdString2 = resourceDictionary["strWinUnLock"]?.ToString();
				_osdOpacity1 = (flag ? _TriggerParam : _UnTriggerParam);
				_osdOpacity2 = (flag ? _UnTriggerParam : _TriggerParam);
				break;
			case 184:
				flag = App.m_MySetting.m_Manager.GetFnKeyStatus() == 1;
				img_name = (flag ? (text + "Fn lock.png") : (text + "Fn unlock.png"));
				LogCtrl.TraceMessage("OSD_FnChange | OnOff = " + flag + ", img_name = " + img_name, "ShowOSD", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\OSD\\OSDManager.cs", 582);
				_osdString1 = resourceDictionary["strFnLock"]?.ToString();
				_osdString2 = resourceDictionary["strFnUnLock"]?.ToString();
				_osdOpacity1 = (flag ? _TriggerParam : _UnTriggerParam);
				_osdOpacity2 = (flag ? _UnTriggerParam : _TriggerParam);
				break;
			case 164:
				flag = airplaneOnOff;
				img_name = (flag ? (text + "airplane-mode.png") : (text + "wifi-on.png"));
				_osdString1 = ((!flag) ? resourceDictionary["strAirplaneModeOff"]?.ToString() : resourceDictionary["strAirplaneModeOn"]?.ToString());
				_osdOpacity1 = 1.0;
				break;
			case 4:
				img_name = "touchpad_1.png";
				break;
			case 5:
				img_name = "touchpad_0.png";
				break;
			}
			System.Windows.Application.Current.Dispatcher.Invoke(delegate
			{
				OSD oSD = new OSD(m_nOsdWidth);
				oSD.SetOSDColor(_OSDDefaultColor);
				string uriString = "pack://application:,,,/osd/image/" + img_name;
				oSD.SetOSDString(_osdString1, _osdString2, _osdOpacity1, _osdOpacity2);
				oSD.img.Source = new BitmapImage(new Uri(uriString));
				oSD.img.Visibility = Visibility.Visible;
				oSD.Visibility = Visibility.Visible;
			});
		}
	}

	public void ShowBLOSD(int scancode)
	{
		if (g_osd_switch != 0)
		{
			string img_name;
			switch (scancode)
			{
			case 59:
				img_name = "OSD_KB_Light_4-01.png";
				break;
			case 60:
				img_name = "OSD_KB_Light_4-02.png";
				break;
			case 61:
				img_name = "OSD_KB_Light_4-03.png";
				break;
			case 62:
				img_name = "OSD_KB_Light_4-04.png";
				break;
			case 63:
				img_name = "OSD_KB_Light_4-05.png";
				break;
			default:
				img_name = "OSD_KB_Light_4-05.png";
				return;
			}
			System.Windows.Application.Current.Dispatcher.Invoke(delegate
			{
				OSD_Vertical oSD_Vertical = new OSD_Vertical();
				oSD_Vertical.SetOSDColor(_OSDDefaultColor);
				string uriString = "pack://application:,,,/osd/image/" + img_name;
				oSD_Vertical.Width = oSD_Vertical.img_bk.Width;
				oSD_Vertical.Height = oSD_Vertical.img_bk.Height;
				oSD_Vertical.img_bk.Source = new BitmapImage(new Uri(uriString));
				oSD_Vertical.img_bk.Visibility = Visibility.Visible;
				oSD_Vertical.Visibility = Visibility.Visible;
			});
		}
	}

	public void ShowBLOSD(string img_name)
	{
		if (g_osd_switch != 0)
		{
			System.Windows.Application.Current.Dispatcher.Invoke(delegate
			{
				OSD_Vertical oSD_Vertical = new OSD_Vertical();
				oSD_Vertical.SetOSDColor(_OSDDefaultColor);
				string uriString = "pack://application:,,,/osd/image/" + img_name;
				oSD_Vertical.Width = oSD_Vertical.img_bk.Width;
				oSD_Vertical.Height = oSD_Vertical.img_bk.Height;
				oSD_Vertical.img_bk.Source = new BitmapImage(new Uri(uriString));
				oSD_Vertical.img_bk.Visibility = Visibility.Visible;
				oSD_Vertical.Visibility = Visibility.Visible;
			});
		}
	}

	public void ShowOSDByName(uint mode)
	{
		string text = "OSD_Universal/";
		string _osdString2 = "";
		ResourceDictionary resourceDictionary = SetResourceDictionary();
		if (g_osd_switch == 0)
		{
			return;
		}
		int customizeTarget = RegistryCtrl.GetCustomizeTarget();
		string img_name;
		if (RegistryCtrl.GetBridgeType() == 0)
		{
			switch (customizeTarget)
			{
			case 4:
				switch (mode)
				{
				default:
					return;
				case 0u:
					img_name = text + "rendering on.png";
					if (!m_ProjectID.IsProjectId_Commercial())
					{
						_osdString2 = resourceDictionary["strOSDGaming"]?.ToString();
					}
					else
					{
						_osdString2 = resourceDictionary["strOSDBalance"]?.ToString();
					}
					break;
				case 1u:
					img_name = text + "office on.png";
					if (!m_ProjectID.IsProjectId_Commercial())
					{
						_osdString2 = resourceDictionary["strOSDOffice"]?.ToString();
					}
					else
					{
						_osdString2 = resourceDictionary["strOSD20db"]?.ToString();
					}
					break;
				case 2u:
					img_name = text + "Turbo on.png";
					_osdString2 = resourceDictionary["strOSDTurbo"]?.ToString();
					break;
				}
				break;
			case 11:
				switch (mode)
				{
				default:
					return;
				case 0u:
					if (!m_ProjectID.IsProjectId_Commercial())
					{
						img_name = text + "gaming on.png";
						_osdString2 = resourceDictionary["strOSDGaming"]?.ToString();
					}
					else
					{
						img_name = text + "Balance.png";
						_osdString2 = resourceDictionary["strOSDBasic"]?.ToString();
					}
					break;
				case 1u:
					img_name = text + "office on.png";
					if (!m_ProjectID.IsProjectId_Commercial())
					{
						_osdString2 = resourceDictionary["strOSDOffice"]?.ToString();
					}
					else
					{
						_osdString2 = resourceDictionary["strOSDSilent"]?.ToString();
					}
					break;
				case 2u:
					img_name = text + "Turbo on.png";
					_osdString2 = resourceDictionary["strOSDTurbo"]?.ToString();
					break;
				}
				break;
			default:
				switch (mode)
				{
				default:
					return;
				case 0u:
					if (!m_ProjectID.IsProjectId_Commercial())
					{
						img_name = text + "gaming on.png";
						_osdString2 = resourceDictionary["strOSDGaming"]?.ToString();
					}
					else
					{
						img_name = text + "Balance.png";
						_osdString2 = resourceDictionary["strOSDBalance"]?.ToString();
					}
					break;
				case 1u:
					img_name = text + "office on.png";
					if (!m_ProjectID.IsProjectId_Commercial())
					{
						_osdString2 = resourceDictionary["strOSDOffice"]?.ToString();
					}
					else
					{
						_osdString2 = resourceDictionary["strOSD20db"]?.ToString();
					}
					break;
				case 2u:
					img_name = text + "Turbo on.png";
					_osdString2 = resourceDictionary["strOSDTurbo"]?.ToString();
					break;
				}
				break;
			}
		}
		else
		{
			switch (mode)
			{
			default:
				return;
			case 0u:
				img_name = text + "gaming on.png";
				if (!m_ProjectID.IsProjectId_Commercial())
				{
					_osdString2 = resourceDictionary["strOSDGaming"]?.ToString();
				}
				else
				{
					_osdString2 = resourceDictionary["strOSDBasic"]?.ToString();
				}
				break;
			case 1u:
				img_name = text + "office on.png";
				if (!m_ProjectID.IsProjectId_Commercial())
				{
					_osdString2 = resourceDictionary["strOSDOffice"]?.ToString();
				}
				else
				{
					_osdString2 = resourceDictionary["strOSDSilent"]?.ToString();
				}
				break;
			case 2u:
				img_name = text + "Turbo on.png";
				_osdString2 = resourceDictionary["strOSDTurbo"]?.ToString();
				break;
			}
		}
		System.Windows.Application.Current.Dispatcher.Invoke(delegate
		{
			OSD oSD = new OSD(m_nOsdWidth);
			string uriString = "pack://application:,,,/osd/image/" + img_name;
			oSD.SetOSDColor(_OSDDefaultColor);
			oSD.SetOSDString("", _osdString2, 0.0, 1.0);
			oSD.img.Source = new BitmapImage(new Uri(uriString));
			oSD.img.Visibility = Visibility.Visible;
			oSD.Visibility = Visibility.Visible;
		});
	}

	public string GetOSDTpString()
	{
		ResourceDictionary resourceDictionary = SetResourceDictionary();
		return resourceDictionary["strPadLock"]?.ToString() + "," + resourceDictionary["strPadUnLock"];
	}

	private void SendOsdStatusToClient(int scancode)
	{
		if (g_osd_switch != 0)
		{
			string text = "";
			string text2 = "";
			switch (scancode)
			{
			default:
				return;
			case 1:
			{
				bool num4 = (Win32.GetKeyState(20) & 1) == 1;
				text = "CapsLock";
				text2 = (num4 ? "Lock" : "UnLock");
				break;
			}
			case 2:
			{
				bool num3 = (Win32.GetKeyState(144) & 1) == 1;
				text = "NumLock";
				text2 = (num3 ? "Lock" : "UnLock");
				break;
			}
			case 3:
			{
				bool num2 = (Win32.GetKeyState(145) & 1) == 1;
				text = "ScrollLock";
				text2 = (num2 ? "Lock" : "UnLock");
				break;
			}
			case 64:
				text = "WinKeyLock";
				text2 = "Lock";
				break;
			case 65:
				text = "WinKeyLock";
				text2 = "UnLock";
				break;
			case 184:
			{
				bool num = App.m_MySetting.m_Manager.GetFnKeyStatus() == 1;
				text = "FnLock";
				text2 = (num ? "Lock" : "UnLock");
				break;
			}
			}
			var data = new
			{
				Function = text,
				Level = text2
			};
			App.m_MQTTService.Publish("OSD/Status", data, retain: false);
		}
	}

	public void SendOsdModeToClient(uint mode)
	{
		if (g_osd_switch != 0)
		{
			string function = "SysPowerMode";
			string text = "";
			switch (mode)
			{
			default:
				return;
			case 1u:
				text = "Performance";
				break;
			case 2u:
				text = "Balanced";
				break;
			case 3u:
				text = "BatterySaver";
				break;
			}
			var data = new
			{
				Function = function,
				Level = text
			};
			App.m_MQTTService.Publish("OSD/Status", data, retain: false);
		}
	}

	public void SendTpOsdStatusToClient(uint status)
	{
		if (g_osd_switch != 0)
		{
			string text = "";
			text = ((status == 1) ? "ON" : "OFF");
			var data = new
			{
				Function = "TouchPad",
				Level = text
			};
			App.m_MQTTService.Publish("OSD/Status", data, retain: false);
		}
	}

	public void SetOsdWay(int scancode, bool airplaneOnOff = false)
	{
		if (m_nBridgeType == 0)
		{
			ShowOSD(scancode, airplaneOnOff);
		}
		else if (m_nBridgeType == 1)
		{
			_ = m_nCustomizeTarget;
			ShowOSD(scancode, airplaneOnOff);
		}
		else
		{
			ShowOSD(scancode, airplaneOnOff);
		}
	}
}
