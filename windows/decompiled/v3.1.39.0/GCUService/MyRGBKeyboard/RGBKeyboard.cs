using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Forms;
using GCUService.MyRgbKeyboard;
using LightingModel;
using Microsoft.Win32;
using MyControlCenter;
using MyControlCenter.MyRgbKeyboard;
using MyECIO;
using Utility;

namespace MyRGBKeyboard;

public class RGBKeyboard
{
	public static LM_Manager m_LM;

	public static MqttClientCtrl m_MQTTClient = null;

	public const string KeyboardTOPIC = "Keyboard/Ctrl";

	public const string Keyboard_Status = "Keyboard/Status";

	private PowerStatus ps = SystemInformation.PowerStatus;

	private HIDKeyboard m_hidkeyboad;

	private object _powerLock = new object();

	private static readonly RGBKeyboard clientService = new RGBKeyboard();

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static RGBKeyboardStauts _RgbKeyboardStatus;

	private CheckAurora aurora = CheckAurora.Instance;

	internal List<Color> DefalutColorList = new List<Color>
	{
		Color.FromArgb(255, 255, 0, 0),
		Color.FromArgb(255, 255, 165, 0),
		Color.FromArgb(255, 255, 255, 0),
		Color.FromArgb(255, 0, 255, 0),
		Color.FromArgb(255, 0, 22, 255),
		Color.FromArgb(255, 0, 0, 255),
		Color.FromArgb(255, 139, 0, 255)
	};

	private object AuroraSwitchLock = new object();

	private object suspendLock = new object();

	public static RGBKeyboard Instance => clientService;

	public event EventHandler HIDLightbarInitedEvent;

	public RGBKeyboard(string DefaultTool, bool IsAppExists)
	{
		RGBKeyboard_Init(DefaultTool, IsAppExists);
	}

	public HIDKeyboard GetHIDKeyboard()
	{
		return m_hidkeyboad;
	}

	public static int GetProjectID()
	{
		byte Data = 0;
		MyEcCtrl.Instance.Read("RGBKeyboard", 1856, ref Data);
		return (byte)Convert.ToUInt64(Data);
	}

	private RGBKeyboard()
	{
		_RgbKeyboardStatus = new RGBKeyboardStauts();
	}

	private void SystemEvents_PowerModeChanged(object sender, PowerModeChangedEventArgs e)
	{
		if (e.Mode == PowerModes.StatusChange)
		{
			if (ps.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Offline)
			{
				m_hidkeyboad?.UnPlugged();
			}
			if (ps.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Online)
			{
				m_hidkeyboad?.Plugged();
			}
		}
	}

	public static RGBKB_Color ConvertJsonRGB2RGBColor(dynamic color)
	{
		bool bCircular = color["isCircular"];
		uint num = color["ColorBlocks"];
		RGBKB_Color result = new RGBKB_Color(bCircular, num);
		for (int i = 0; i < num; i++)
		{
			result.ColorBuffer[i].ID = color["ColorBuffer"][i]["ID"];
			result.ColorBuffer[i].R = color["ColorBuffer"][i]["R"];
			result.ColorBuffer[i].G = color["ColorBuffer"][i]["G"];
			result.ColorBuffer[i].B = color["ColorBuffer"][i]["B"];
		}
		return result;
	}

	public void Event_LM(RGBKB_Event_Data event_data)
	{
		if (event_data.event_id != RGBKB_EventID.Brightness_update)
		{
			return;
		}
		int brightness = event_data.event_data[0];
		System.Windows.Application.Current.Dispatcher.Invoke(delegate
		{
			_ = new
			{
				MqttID = "KeyboardUserId",
				function = "UpdateBrightness",
				level = brightness
			};
			if (m_hidkeyboad != null)
			{
				_RgbKeyboardStatus.solution = m_LM.m_KB_Solution.ToString();
				_RgbKeyboardStatus.type = m_LM.m_KB_Type.ToString();
				_RgbKeyboardStatus.powerStatus = m_hidkeyboad?.GetPowerStatus().ToString();
				_RgbKeyboardStatus.brightNess = m_hidkeyboad?.GetBrightness().ToString();
				_RgbKeyboardStatus.ACBrightness = m_hidkeyboad?._AC_LightLevel.ToString();
				_RgbKeyboardStatus.DCBrightness = m_hidkeyboad?._DC_LightLevel.ToString();
				_RgbKeyboardStatus.welcomeStatus = m_hidkeyboad?.GetWelcomeStatus();
				_RgbKeyboardStatus.welcomeDirectionStatus = m_hidkeyboad?.GetWelcomeDirectionStatus();
				_RgbKeyboardStatus.auroraStatus = aurora.GetAuroraStauts();
				m_MQTTClient.Publish("Keyboard/Status", _RgbKeyboardStatus);
			}
			if (event_data.envet_data_len == 1)
			{
				LogCtrl.Write("RGBKeyboard|Event_LM : UpdateStatusToOSD level: " + brightness);
				UpdateStatusToOSD(brightness);
			}
			else
			{
				LogCtrl.Write("Only update UI");
			}
		});
	}

	public void UpdateStatusToOSD(int BL_Level)
	{
		string function = "KeyBoardBrghtiness";
		string text = "";
		string img_name;
		switch (BL_Level)
		{
		case 0:
			img_name = "OSD_KB_Light_4-01.png";
			text = "0";
			break;
		case 1:
			img_name = "OSD_KB_Light_4-02.png";
			text = "25";
			break;
		case 2:
			img_name = "OSD_KB_Light_4-03.png";
			text = "50";
			break;
		case 3:
			img_name = "OSD_KB_Light_4-04.png";
			text = "75";
			break;
		case 4:
			img_name = "OSD_KB_Light_4-05.png";
			text = "100";
			break;
		default:
			img_name = "OSD_KB_Light_4-01.png";
			text = "0";
			break;
		}
		if (m_hidkeyboad is _2p1ndKeyboard_KC)
		{
			var data = new
			{
				Function = function,
				Level = text
			};
			m_MQTTClient.Publish("OSD/Status", data, retain: false);
		}
		else
		{
			App.m_Osd.ShowBLOSD(img_name);
		}
	}

	public void RGBKeyboard_Init(string DefaulTool, bool IsAppExists)
	{
		LogCtrl.Write("RGBKeyboard | RGBKeyboard_Init");
		if (m_LM != null)
		{
			return;
		}
		m_LM = new LM_Manager();
		if (m_LM.LM_Init(DefaulTool))
		{
			m_hidkeyboad = HIDKeyboardFactory.CreateHIDDevice(m_LM);
			if (ps.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Offline)
			{
				m_hidkeyboad?.InitalizeKeyboardEffect(unplug: true);
				m_hidkeyboad?.InitalizeWelcomeKeyboardEffect(RGBKB_PowerStatus.On, IsAppExists, unplug: true);
			}
			else
			{
				m_hidkeyboad?.InitalizeKeyboardEffect();
				m_hidkeyboad?.InitalizeWelcomeKeyboardEffect(RGBKB_PowerStatus.On, IsAppExists);
			}
		}
	}

	private void AuroraStatusChanged(object auroraEnable, EventArgs e)
	{
	}

	public void RGBKeyboard_Init()
	{
		LogCtrl.Write("RGBKeyboard | RGBKeyboard_Init");
		CheckAurora checkAurora = aurora;
		checkAurora.AuroraStatusChanged = (ErrorEventHandler)Delegate.Combine(checkAurora.AuroraStatusChanged, new ErrorEventHandler(AuroraStatusChanged));
		if (m_LM == null)
		{
			m_LM = new LM_Manager();
			if (m_LM.LM_Init())
			{
				m_hidkeyboad = HIDKeyboardFactory.CreateHIDDevice(m_LM);
				if (m_LM.m_KB_Type.ToString() == RGBKB_Type.FourZone.ToString() || m_LM.m_KB_Type.ToString() == RGBKB_Type.FourZoneSingleColor.ToString())
				{
					CheckAurora.Instance.SetAuroraSwtich(enable: false);
				}
				if (ps.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Offline)
				{
					m_hidkeyboad?.InitalizeKeyboardEffect(unplug: true);
				}
				else
				{
					m_hidkeyboad?.InitalizeKeyboardEffect();
				}
				if (m_hidkeyboad != null)
				{
					m_hidkeyboad.m_Layout_Event_handler += Event_LM;
					SystemEvents.PowerModeChanged += SystemEvents_PowerModeChanged;
					WMIEC.LMScanCodeEvent = (WMIEC.LM_ScanCode_EventHander)Delegate.Remove(WMIEC.LMScanCodeEvent, new WMIEC.LM_ScanCode_EventHander(ScanCode_Hnadler));
					WMIEC.LMScanCodeEvent = (WMIEC.LM_ScanCode_EventHander)Delegate.Combine(WMIEC.LMScanCodeEvent, new WMIEC.LM_ScanCode_EventHander(ScanCode_Hnadler));
				}
			}
			else
			{
				CheckAurora.Instance.SetAuroraSwtich(enable: false);
			}
		}
		else
		{
			_RgbKeyboardStatus.solution = m_LM.m_KB_Solution.ToString();
			_RgbKeyboardStatus.type = m_LM.m_KB_Type.ToString();
			m_hidkeyboad = HIDKeyboardFactory.CreateHIDDevice(m_LM);
			if (ps.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Offline)
			{
				m_hidkeyboad?.InitalizeKeyboardEffect(unplug: true);
			}
			else
			{
				m_hidkeyboad?.InitalizeKeyboardEffect();
			}
			if (m_hidkeyboad != null)
			{
				m_hidkeyboad.m_Layout_Event_handler += Event_LM;
				SystemEvents.PowerModeChanged += SystemEvents_PowerModeChanged;
				WMIEC.LMScanCodeEvent = (WMIEC.LM_ScanCode_EventHander)Delegate.Remove(WMIEC.LMScanCodeEvent, new WMIEC.LM_ScanCode_EventHander(ScanCode_Hnadler));
				WMIEC.LMScanCodeEvent = (WMIEC.LM_ScanCode_EventHander)Delegate.Combine(WMIEC.LMScanCodeEvent, new WMIEC.LM_ScanCode_EventHander(ScanCode_Hnadler));
			}
		}
	}

	public static void RGBKeyboard_DeInit()
	{
		if (m_LM != null)
		{
			m_LM.LM_DeInit();
			m_LM = null;
		}
	}

	private void ScanCode_Hnadler(int scancode)
	{
		LogCtrl.Write("Keybaord Get Scancode : " + scancode);
		if (!CheckAurora.Instance.GetAuroraStauts() && m_hidkeyboad != null)
		{
			m_hidkeyboad?.SetBrinessByScanCode(scancode);
			m_hidkeyboad?.SetChinaMode(scancode);
		}
	}

	public async void RGBKeyboard_SetEffectALL(dynamic data)
	{
		if (m_LM == null)
		{
			return;
		}
		RGBKB_Mode mode = data["mode"];
		if (mode.Equals(RGBKB_Mode.Welcome))
		{
			if (m_hidkeyboad != null && m_hidkeyboad?.SetWelcomeEffect(data))
			{
				m_hidkeyboad.SetMode(mode);
				m_hidkeyboad?.RunWelcomeEffect();
			}
		}
		else if (m_hidkeyboad != null && m_hidkeyboad?.SetEffect(data))
		{
			m_hidkeyboad.SetMode(mode);
			m_hidkeyboad?.RunEffct(0);
		}
	}

	public void RGBKeyboard_SetEffectLight_ACDC(dynamic data)
	{
		if (data["ACBrightness"] != null && data["DCBrightness"] != null)
		{
			uint aCBrightness = Convert.ToUInt32(data["ACBrightness"]);
			uint dCBrighteness = Convert.ToUInt32(data["DCBrightness"]);
			m_hidkeyboad?.SetBrightness_ACDC(aCBrightness, dCBrighteness);
		}
	}

	public void RGBKeyboard_SetEffectLight(dynamic data)
	{
		RGBKB_Mode mode = data["mode"];
		if (mode.Equals(RGBKB_Mode.Welcome))
		{
			if ((m_hidkeyboad?.SetWelcomeEffect(data)))
			{
				m_hidkeyboad.SetMode(mode);
				m_hidkeyboad?.RunWelcomeEffect();
			}
		}
		else if (m_LM != null)
		{
			uint brightness = data["light"];
			m_hidkeyboad?.SetMode(mode);
			m_hidkeyboad?.SetBrightness(brightness);
		}
	}

	public static void RGBKeyboard_SetColor(dynamic data)
	{
		if (m_LM != null)
		{
			RGBKB_Mode layout_mode = data["mode"];
			RGBKB_Effect layout_effect = data["effect"];
			RGBKB_Color layout_color = RGBKeyboard.ConvertJsonRGB2RGBColor(data["color"]);
			if (m_LM.m_KB_Type == RGBKB_Type.FourZoneSingleColor)
			{
				LogCtrl.TraceMessage("FourZoneSingleColor keyboard, can not set color", "RGBKeyboard_SetColor", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\RGBKeyboard.cs", 741);
			}
			else
			{
				m_LM.LM_SetColor(layout_mode, layout_effect, layout_color);
			}
		}
	}

	public static void RGBKeyboard_SaveLightingLevel(dynamic data)
	{
		if (m_LM != null)
		{
			m_LM.LM_SaveLightingLevel(0u);
		}
	}

	public async void OnMqttMessage(string topic, string msg)
	{
		_ = 2;
		try
		{
			if (!(topic == "Keyboard/Ctrl"))
			{
				return;
			}
			dynamic val = await Json.ToObjectAsync<object>(msg);
			string text = Convert.ToString(val["function"]);
			string text2 = Convert.ToString(val["Action"]);
			if (text2 != null && text2 == "GETSTATUS")
			{
				try
				{
					if (m_LM != null)
					{
						if (m_LM.m_KB_Type != RGBKB_Type.SingleZone)
						{
							_RgbKeyboardStatus.solution = m_LM.m_KB_Solution.ToString();
							_RgbKeyboardStatus.type = m_LM.m_KB_Type.ToString();
							_RgbKeyboardStatus.brightNess = m_hidkeyboad?.GetBrightness().ToString();
							_RgbKeyboardStatus.ACBrightness = m_hidkeyboad?._AC_LightLevel.ToString();
							_RgbKeyboardStatus.DCBrightness = m_hidkeyboad?._DC_LightLevel.ToString();
							_RgbKeyboardStatus.powerStatus = m_hidkeyboad?.GetPowerStatus().ToString();
							_RgbKeyboardStatus.welcomeStatus = m_hidkeyboad?.GetWelcomeStatus();
							_RgbKeyboardStatus.welcomeDirectionStatus = m_hidkeyboad?.GetWelcomeDirectionStatus();
							_RgbKeyboardStatus.auroraStatus = aurora.GetAuroraStauts();
							_RgbKeyboardStatus.auroraExist = aurora.GetAuroraExists();
						}
						else if (m_LM.m_KB_Type == RGBKB_Type.SingleZone && m_hidkeyboad != null)
						{
							_RgbKeyboardStatus.powerStatus = m_hidkeyboad?.GetPowerStatus().ToString();
							_RgbKeyboardStatus.solution = m_LM.m_KB_Solution.ToString();
							_RgbKeyboardStatus.type = m_LM.m_KB_Type.ToString();
							_RgbKeyboardStatus.SingleZonePowerSupport = Convert.ToBoolean(m_hidkeyboad?.GetSingleZonePowerSupport());
							_RgbKeyboardStatus.brightNess = m_hidkeyboad?.GetBrightness().ToString();
							_RgbKeyboardStatus.MonochromeIndex = m_hidkeyboad.GetMonochromeIndex().ToString();
							_RgbKeyboardStatus.ManualIndex1 = m_hidkeyboad.GetManualIndex1().ToString();
							_RgbKeyboardStatus.ManualIndex2 = m_hidkeyboad.GetManualIndex2().ToString();
							_RgbKeyboardStatus.ManualIndex3 = m_hidkeyboad.GetManualIndex3().ToString();
							_RgbKeyboardStatus.ManualIndex4 = m_hidkeyboad.GetManualIndex4().ToString();
							_RgbKeyboardStatus.ManualIndex5 = m_hidkeyboad.GetManualIndex5().ToString();
							_RgbKeyboardStatus.ManualIndex6 = m_hidkeyboad.GetManualIndex6().ToString();
							_RgbKeyboardStatus.ManualInterval = m_hidkeyboad.GetManualInterval().ToString();
							_RgbKeyboardStatus.BreathingIndex = m_hidkeyboad.GetBreathingIndex().ToString();
							_RgbKeyboardStatus.DefaultData = m_hidkeyboad.GetDefaultData();
							_RgbKeyboardStatus.color = m_hidkeyboad.GetLayoutColor();
						}
						m_MQTTClient.Publish("Keyboard/Status", _RgbKeyboardStatus);
					}
					return;
				}
				catch
				{
					return;
				}
			}
			if (text == null)
			{
				return;
			}
			switch (text)
			{
			case "SetAurora":
			{
				bool flag = val["AuroraSwitch"];
				if (!Monitor.TryEnter(AuroraSwitchLock, 1000))
				{
					break;
				}
				try
				{
					if (!flag)
					{
						if (m_hidkeyboad != null)
						{
							aurora.SetAuroraSwtich(flag);
							Thread.Sleep(250);
							m_hidkeyboad.RunEffct(0);
						}
					}
					else
					{
						m_hidkeyboad?._KeyboardControl?.StopMusicTransfer();
						m_hidkeyboad?._KeyboardControl?.Set_ITE_Effect_Type_ApMode_Stop();
						Thread.Sleep(250);
						aurora.SetAuroraSwtich(flag);
					}
					break;
				}
				catch
				{
					break;
				}
				finally
				{
					Monitor.Exit(AuroraSwitchLock);
				}
			}
			case "Init":
				RGBKeyboard_Init();
				break;
			case "DeInit":
				RGBKeyboard_DeInit();
				break;
			case "SetPower":
			{
				RGBKB_PowerStatus rGBKB_PowerStatus = val["powerstatus"];
				if (!MyEcCtrl.Instance.IsChinaMode())
				{
					byte Data = 0;
					MyEcCtrl.Instance.Read(GetType().Name, 1922, ref Data);
					Data |= 0x40;
					MyEcCtrl.Instance.Write(GetType().Name, 1922, Data);
				}
				if (rGBKB_PowerStatus != RGBKB_PowerStatus.On)
				{
					Task task = Task.Run(delegate
					{
						m_hidkeyboad?.CloseAnimation();
					});
					Task.WaitAll(task);
					m_hidkeyboad?.SetPowerStatus(rGBKB_PowerStatus);
				}
				else
				{
					m_hidkeyboad?.SetPowerStatus(rGBKB_PowerStatus);
				}
				if (m_LM.m_KB_Type != RGBKB_Type.SingleZone)
				{
					_RgbKeyboardStatus.solution = m_LM.m_KB_Solution.ToString();
					_RgbKeyboardStatus.type = m_LM.m_KB_Type.ToString();
					_RgbKeyboardStatus.brightNess = m_hidkeyboad?.GetBrightness().ToString();
					_RgbKeyboardStatus.powerStatus = m_hidkeyboad?.GetPowerStatus().ToString();
					_RgbKeyboardStatus.welcomeStatus = m_hidkeyboad?.GetWelcomeStatus();
					_RgbKeyboardStatus.welcomeDirectionStatus = m_hidkeyboad?.GetWelcomeDirectionStatus();
					_RgbKeyboardStatus.auroraStatus = aurora.GetAuroraStauts();
					_RgbKeyboardStatus.effect = m_hidkeyboad?.GetAllKeyboardStatus().save_effect.ToString();
					_RgbKeyboardStatus.powerstatus = ((m_hidkeyboad?.GetPowerStatus().ToString() == "On") ? 1 : 0);
					_RgbKeyboardStatus.light = m_hidkeyboad?.GetBrightness().ToString();
					_RgbKeyboardStatus.speed = m_hidkeyboad?.GetAllKeyboardStatus().save_speed.ToString();
					_RgbKeyboardStatus.direction = m_hidkeyboad?.GetAllKeyboardStatus().save_direction.ToString();
					RGBKeyboardStauts rgbKeyboardStatus = _RgbKeyboardStatus;
					rgbKeyboardStatus.rkgcolor = await Json.StringifyAsync(m_hidkeyboad?.GetAllKeyboardStatus().save_layout_color);
					if (_RgbKeyboardStatus.rkgcolor == null)
					{
						RGBKB_Color rGBKB_Color = new RGBKB_Color
						{
							ColorBlocks = 7u,
							isCircular = true
						};
						List<RGB_S> list = new List<RGB_S>();
						int num = 0;
						foreach (Color defalutColor in DefalutColorList)
						{
							list.Add(new RGB_S
							{
								ID = (uint)num,
								R = defalutColor.R,
								G = defalutColor.G,
								B = defalutColor.B
							});
							num++;
						}
						rGBKB_Color.ColorBuffer = list.ToArray();
						rgbKeyboardStatus = _RgbKeyboardStatus;
						rgbKeyboardStatus.rkgcolor = await Json.StringifyAsync(rGBKB_Color);
					}
				}
				else if (m_LM.m_KB_Type == RGBKB_Type.SingleZone && m_hidkeyboad != null)
				{
					_RgbKeyboardStatus.powerStatus = m_hidkeyboad?.GetPowerStatus().ToString();
					_RgbKeyboardStatus.solution = m_LM.m_KB_Solution.ToString();
					_RgbKeyboardStatus.type = m_LM.m_KB_Type.ToString();
					_RgbKeyboardStatus.SingleZonePowerSupport = m_hidkeyboad.GetSingleZonePowerSupport();
					_RgbKeyboardStatus.brightNess = m_hidkeyboad?.GetBrightness().ToString();
					_RgbKeyboardStatus.MonochromeIndex = m_hidkeyboad.GetMonochromeIndex().ToString();
					_RgbKeyboardStatus.ManualIndex1 = m_hidkeyboad.GetManualIndex1().ToString();
					_RgbKeyboardStatus.ManualIndex2 = m_hidkeyboad.GetManualIndex2().ToString();
					_RgbKeyboardStatus.ManualIndex3 = m_hidkeyboad.GetManualIndex3().ToString();
					_RgbKeyboardStatus.ManualIndex4 = m_hidkeyboad.GetManualIndex4().ToString();
					_RgbKeyboardStatus.ManualIndex5 = m_hidkeyboad.GetManualIndex5().ToString();
					_RgbKeyboardStatus.ManualIndex6 = m_hidkeyboad.GetManualIndex6().ToString();
					_RgbKeyboardStatus.ManualInterval = m_hidkeyboad.GetManualInterval().ToString();
					_RgbKeyboardStatus.BreathingIndex = m_hidkeyboad.GetBreathingIndex().ToString();
					_RgbKeyboardStatus.DefaultData = m_hidkeyboad.GetDefaultData();
				}
				if (m_hidkeyboad != null)
				{
					m_MQTTClient.Publish("Keyboard/Status", _RgbKeyboardStatus);
				}
				break;
			}
			case "SetEffectALL":
				RGBKeyboard_SetEffectALL(val);
				break;
			case "SetColor":
				RGBKeyboard_SetColor(val);
				break;
			case "SetLightingLevel":
				if (m_hidkeyboad is _2p1ndKeyboard_KC || m_hidkeyboad is _2p1ndKeyboard_QC)
				{
					RGBKeyboard_SetEffectLight_ACDC(val);
				}
				else
				{
					RGBKeyboard_SetEffectLight(val);
				}
				break;
			case "SaveLightingLevel":
				RGBKeyboard_SaveLightingLevel(val);
				break;
			case "SetPowerSaving":
				break;
			case "GetEffect":
				break;
			case "GetLightingLevel":
				break;
			case "GetFirmwareVersion":
				break;
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("exception: " + ex, "OnMqttMessage", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\RGBKeyboard.cs", 1064);
		}
	}

	public static void OnMqttDisconnection()
	{
	}

	public bool init()
	{
		m_MQTTClient = MqttClientCtrl.Instance;
		RGBKeyboard_Init();
		if (m_MQTTClient != null)
		{
			return true;
		}
		return false;
	}

	public void EnableByService()
	{
	}

	public void DisableByService()
	{
	}

	public void Resume()
	{
		if (!CheckAurora.Instance.GetAuroraStauts() && m_hidkeyboad != null)
		{
			LogCtrl.Write("RGBKeybaord From S4 Resume");
			if (m_hidkeyboad._KeyboardControl != null)
			{
				m_hidkeyboad?._KeyboardControl?.Set_ITE_Effect_Type_ApMode_Stop();
			}
			m_hidkeyboad?.RunEffct(0);
			LogCtrl.Write("KeybaordTest");
			HIDKeyboard hidkeyboad = m_hidkeyboad;
			if (hidkeyboad != null && hidkeyboad.GetPowerStatus() == RGBKB_PowerStatus.Off)
			{
				m_hidkeyboad?.SetPowerStatus(RGBKB_PowerStatus.Off);
			}
		}
	}

	public void Suspend()
	{
		if (!Monitor.TryEnter(suspendLock, 3000))
		{
			return;
		}
		try
		{
			Thread thread = new Thread((ThreadStart)delegate
			{
				m_hidkeyboad?.CloseAnimation();
			});
			thread.Start();
			thread.Join();
		}
		catch (Exception)
		{
		}
		finally
		{
			Monitor.Exit(suspendLock);
		}
	}

	public void Restore()
	{
		string directoryName = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName;
		string text = null;
		directoryName = LogCtrl.GetParentDirectoryPath(directoryName, 2);
		text = "/s \"" + directoryName + "\\RGBKeyboard.reg\"";
		Process.Start("regedit.exe", text).WaitForExit();
		new Task<int>(delegate
		{
			int num = 0;
			RGBKeyboard_Init();
			do
			{
				GetHIDKeyboard()?.GetInitSuccessful();
				Thread.Sleep(300);
				num++;
			}
			while (num != 20);
			return num;
		}).Start();
	}

	public void Uninstall()
	{
		m_hidkeyboad?.Uninstall();
	}
}
