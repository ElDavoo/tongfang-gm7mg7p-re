using System;
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

public class HIDRGBLightbar
{
	public static LM_Manager m_LB;

	public static MqttClientCtrl m_MQTTClient = null;

	public const string HidLightbarTOPIC = "HidLightbar/Ctrl";

	public const string HidLightbar_Status = "HidLightbar/Status";

	public const string OSD_Status = "OSD/Status";

	private PowerStatus ps = SystemInformation.PowerStatus;

	private HIDKeyboard m_hidLighBar;

	private object _powerLock = new object();

	private static readonly HIDRGBLightbar clientService = new HIDRGBLightbar();

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static RGBKeyboardStauts _HidLightbarStatus;

	private object suspendLock = new object();

	public static HIDRGBLightbar Instance => clientService;

	public event EventHandler HIDLightbarInitedEvent;

	public HIDRGBLightbar(string DefaultTool, bool IsAppExists)
	{
		RGBHidLightbar_Init(DefaultTool, IsAppExists);
	}

	public HIDKeyboard GetHIDLightbar()
	{
		return m_hidLighBar;
	}

	public static int GetProjectID()
	{
		byte Data = 0;
		MyEcCtrl.Instance.Read("HIDRGBLightbar", 1856, ref Data);
		return (byte)Convert.ToUInt64(Data);
	}

	private HIDRGBLightbar()
	{
		_HidLightbarStatus = new RGBKeyboardStauts();
	}

	private void SystemEvents_PowerModeChanged(object sender, PowerModeChangedEventArgs e)
	{
		if (e.Mode == PowerModes.StatusChange)
		{
			if (ps.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Offline)
			{
				m_hidLighBar?.UnPlugged();
			}
			if (ps.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Online)
			{
				m_hidLighBar?.Plugged();
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
			if (m_hidLighBar != null)
			{
				_HidLightbarStatus.powerStatus = m_hidLighBar?.GetPowerStatus().ToString();
				_HidLightbarStatus.brightNess = m_hidLighBar?.GetBrightness().ToString();
				_HidLightbarStatus.welcomeStatus = m_hidLighBar?.GetWelcomeStatus();
				_HidLightbarStatus.welcomeDirectionStatus = m_hidLighBar?.GetWelcomeDirectionStatus();
				m_MQTTClient.Publish("HidLightbar/Status", _HidLightbarStatus);
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

	public static void UpdateStatusToOSD(int BL_Level)
	{
		App.m_Osd.ShowBLOSD(BL_Level switch
		{
			0 => "OSD_KB_Light_4-01.png", 
			1 => "OSD_KB_Light_4-02.png", 
			2 => "OSD_KB_Light_4-03.png", 
			3 => "OSD_KB_Light_4-04.png", 
			4 => "OSD_KB_Light_4-05.png", 
			_ => "OSD_KB_Light_4-01.png", 
		});
	}

	public void RGBHidLightbar_Init(string DefaulTool, bool IsAppExists)
	{
		LogCtrl.Write("RGBHidLightbar | RGBHidLightbar_Init");
		if (m_LB != null)
		{
			return;
		}
		m_LB = new LM_Manager();
		if (m_LB.LB_Init())
		{
			m_hidLighBar = HIDKeyboardFactory.CreateHIDDevice(m_LB);
			if (ps.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Offline)
			{
				m_hidLighBar?.InitalizeKeyboardEffect(unplug: true);
				m_hidLighBar?.InitalizeWelcomeKeyboardEffect(RGBKB_PowerStatus.On, IsAppExists, unplug: true);
			}
			else
			{
				m_hidLighBar?.InitalizeKeyboardEffect();
				m_hidLighBar?.InitalizeWelcomeKeyboardEffect(RGBKB_PowerStatus.On, IsAppExists);
			}
			if (m_hidLighBar != null)
			{
				m_hidLighBar.m_Layout_Event_handler += Event_LM;
				SystemEvents.PowerModeChanged += SystemEvents_PowerModeChanged;
				WMIEC.LMScanCodeEvent = (WMIEC.LM_ScanCode_EventHander)Delegate.Remove(WMIEC.LMScanCodeEvent, new WMIEC.LM_ScanCode_EventHander(ScanCode_Hnadler));
				WMIEC.LMScanCodeEvent = (WMIEC.LM_ScanCode_EventHander)Delegate.Combine(WMIEC.LMScanCodeEvent, new WMIEC.LM_ScanCode_EventHander(ScanCode_Hnadler));
			}
			if (this.HIDLightbarInitedEvent != null)
			{
				this.HIDLightbarInitedEvent(m_hidLighBar, null);
			}
		}
	}

	public void RGBHidLightbar_Init()
	{
		LogCtrl.Write("RGBHidLightbar | RGBHidLightbar_Init");
		if (m_LB == null)
		{
			m_LB = new LM_Manager();
			if (m_LB.LB_Init())
			{
				m_hidLighBar = HIDKeyboardFactory.CreateHIDDevice(m_LB);
				if (ps.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Offline)
				{
					LogCtrl.Write("HidLightbar : DC Mode Init");
					m_hidLighBar?.InitalizeKeyboardEffect(unplug: true);
				}
				else
				{
					LogCtrl.Write("HidLightbar : AC Mode Init");
					m_hidLighBar?.InitalizeKeyboardEffect();
				}
				if (m_hidLighBar != null)
				{
					m_hidLighBar.m_Layout_Event_handler += Event_LM;
					SystemEvents.PowerModeChanged += SystemEvents_PowerModeChanged;
					WMIEC.LMScanCodeEvent = (WMIEC.LM_ScanCode_EventHander)Delegate.Remove(WMIEC.LMScanCodeEvent, new WMIEC.LM_ScanCode_EventHander(ScanCode_Hnadler));
					WMIEC.LMScanCodeEvent = (WMIEC.LM_ScanCode_EventHander)Delegate.Combine(WMIEC.LMScanCodeEvent, new WMIEC.LM_ScanCode_EventHander(ScanCode_Hnadler));
				}
				if (this.HIDLightbarInitedEvent != null)
				{
					this.HIDLightbarInitedEvent(m_hidLighBar, null);
				}
			}
		}
		if (m_LB != null)
		{
			_HidLightbarStatus.solution = m_LB.m_KB_Solution.ToString();
			_HidLightbarStatus.type = m_LB.m_KB_Type.ToString();
		}
	}

	public static void RGBLightbar_DeInit()
	{
		if (m_LB != null)
		{
			m_LB = null;
		}
	}

	private void ScanCode_Hnadler(int scancode)
	{
		LogCtrl.Write("Lightbar Get Scancode : " + scancode);
		if (m_hidLighBar != null)
		{
			m_hidLighBar?.SetChinaMode(scancode);
		}
	}

	public async void RGBKeyboard_SetEffectALL(dynamic data)
	{
		if (m_LB == null)
		{
			return;
		}
		RGBKB_Mode mode = data["mode"];
		if (mode.Equals(RGBKB_Mode.Welcome))
		{
			if ((m_hidLighBar?.SetWelcomeEffect(data)))
			{
				m_hidLighBar?.SetMode(mode);
				m_hidLighBar?.RunWelcomeEffect();
			}
		}
		else if (m_hidLighBar != null && m_hidLighBar.SetEffect(data))
		{
			m_hidLighBar?.SetMode(mode);
			m_hidLighBar?.RunEffct(0);
		}
	}

	public void RGBKeyboard_SetEffectLight(dynamic data)
	{
		RGBKB_Mode mode = data["mode"];
		if (mode.Equals(RGBKB_Mode.Welcome))
		{
			if ((m_hidLighBar?.SetWelcomeEffect(data)))
			{
				m_hidLighBar?.SetMode(mode);
				m_hidLighBar?.RunWelcomeEffect();
			}
		}
		else if (m_LB != null)
		{
			uint brightness = data["light"];
			m_hidLighBar?.SetMode(mode);
			m_hidLighBar?.SetBrightness(brightness);
		}
	}

	public static void RGBKeyboard_SetColor(dynamic data)
	{
		if (m_LB != null)
		{
			RGBKB_Mode layout_mode = data["mode"];
			RGBKB_Effect layout_effect = data["effect"];
			RGBKB_Color layout_color = HIDRGBLightbar.ConvertJsonRGB2RGBColor(data["color"]);
			m_LB.LM_SetColor(layout_mode, layout_effect, layout_color);
		}
	}

	public static void RGBKeyboard_SaveLightingLevel(dynamic data)
	{
		if (m_LB != null)
		{
			m_LB.LM_SaveLightingLevel(0u);
		}
	}

	public async void OnMqttMessage(string topic, string msg)
	{
		try
		{
			if (!(topic == "HidLightbar/Ctrl"))
			{
				return;
			}
			dynamic val = await Json.ToObjectAsync<object>(msg);
			string text = Convert.ToString(val["function"]);
			string text2 = Convert.ToString(val["Action"]);
			if (text2 != null && text2 == "GETSTATUS")
			{
				_HidLightbarStatus.brightNess = m_hidLighBar?.GetBrightness().ToString();
				_HidLightbarStatus.powerStatus = m_hidLighBar?.GetPowerStatus().ToString();
				_HidLightbarStatus.welcomeStatus = m_hidLighBar?.GetWelcomeStatus();
				_HidLightbarStatus.welcomeDirectionStatus = m_hidLighBar?.GetWelcomeDirectionStatus();
				m_MQTTClient?.Publish("HidLightbar/Status", _HidLightbarStatus);
			}
			else
			{
				if (text == null)
				{
					return;
				}
				switch (text)
				{
				case "Init":
					RGBHidLightbar_Init();
					break;
				case "DeInit":
					RGBLightbar_DeInit();
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
							m_hidLighBar?.CloseAnimation();
						});
						Task.WaitAll(task);
						m_hidLighBar?.SetPowerStatus(rGBKB_PowerStatus);
					}
					else
					{
						m_hidLighBar?.SetPowerStatus(rGBKB_PowerStatus);
					}
					_HidLightbarStatus.brightNess = m_hidLighBar?.GetBrightness().ToString();
					_HidLightbarStatus.powerStatus = m_hidLighBar?.GetPowerStatus().ToString();
					_HidLightbarStatus.welcomeStatus = m_hidLighBar?.GetWelcomeStatus();
					_HidLightbarStatus.welcomeDirectionStatus = m_hidLighBar?.GetWelcomeDirectionStatus();
					if (m_hidLighBar != null)
					{
						m_MQTTClient.Publish("HidLightbar/Status", _HidLightbarStatus);
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
					RGBKeyboard_SetEffectLight(val);
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
		}
		catch
		{
		}
	}

	public static void OnMqttDisconnection()
	{
	}

	public bool init()
	{
		m_MQTTClient = MqttClientCtrl.Instance;
		RGBHidLightbar_Init();
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
		if (!CheckAurora.Instance.GetAuroraStauts() && m_hidLighBar != null)
		{
			LogCtrl.Write("HidLightbar From S4 Resume");
			m_hidLighBar?._KeyboardControl.Set_ITE_Effect_Type_ApMode_Stop();
			m_hidLighBar?.RunEffct(0);
			HIDKeyboard hidLighBar = m_hidLighBar;
			if (hidLighBar != null && hidLighBar.GetPowerStatus() == RGBKB_PowerStatus.Off)
			{
				m_hidLighBar?.SetPowerStatus(RGBKB_PowerStatus.Off);
			}
		}
	}

	public void Suspend()
	{
		if (!Monitor.TryEnter(suspendLock, 5000))
		{
			return;
		}
		try
		{
			Thread thread = new Thread((ThreadStart)delegate
			{
				m_hidLighBar?.CloseAnimation();
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

	public void Uninstall()
	{
		SettingsStorageExtensions.DeleteRGBKeyboardRegistry();
	}
}
