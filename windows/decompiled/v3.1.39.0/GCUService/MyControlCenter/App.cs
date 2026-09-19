using System;
using System.CodeDom.Compiler;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using Define;
using GCUService.MyRgbKeyboard;
using GCUService.MySetting;
using GCUService.MySystem;
using GCUService.WCFService;
using LightingModel;
using Microsoft.Win32;
using MyControlCenter.MyFan.FanTable;
using MyControlCenter.MyRgbKeyboard;
using MyECIO;
using MyRGBKeyboard;
using Utility;
using Workaround;
using uPLibrary.Networking.M2Mqtt.Messages;

namespace MyControlCenter;

public class App : Application
{
	public static TrayCtrl m_TrayCtrl;

	public static MySystemCtrl m_MySystem;

	private MyFanTableCtrl m_MyFanTable;

	private MyFanCtrl m_MyFan;

	private MyRgbLightbarCtrl m_RGBLB;

	public static MySettingCtrl m_MySetting;

	public static OSDManager m_Osd;

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static WMIEC m_Wmi = new WMIEC();

	private PowerModeEvent m_PowerModeEvent;

	public static MqttClientCtrl m_MQTTService = MqttClientCtrl.Instance;

	public static bool bDebug = false;

	private bool bIsExit;

	private RGBKeyboard rgbkeyboard;

	private HIDRGBLightbar hidrgblightbar;

	private Dictionary<string, Task> TasksMoniter = new Dictionary<string, Task>();

	private Dictionary<string, Thread> ThreadList = new Dictionary<string, Thread>();

	private List<string> ApplicationNames = new List<string> { "MyRGBKeyboard", "MySystem", "MyFan", "MySetting", "MyRgbLightbar" };

	private WCFServiceHost host;

	public static int OsdOnly = 0;

	public static int m_nCustomizeTarget = 1;

	public static int m_nBridgeType = 0;

	private string m_sRegPath = "\\OEM\\GamingCenter2";

	private Stopwatch sw = new Stopwatch();

	private static int m_FirstTime = 0;

	private bool _contentLoaded;

	private void Application_Startup(object sender, StartupEventArgs e)
	{
		RenderOptions.ProcessRenderMode = RenderMode.SoftwareOnly;
		LogCtrl.EnableLog();
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write("[Application_Startup] Start");
		try
		{
			OsdOnly = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "OsdOnly", 0);
		}
		catch
		{
		}
		m_nCustomizeTarget = RegistryCtrl.GetCustomizeTarget();
		m_nBridgeType = RegistryCtrl.GetBridgeType();
		m_PowerModeEvent = new PowerModeEvent();
		m_MySystem = new MySystemCtrl();
		m_MyFanTable = MyFanTableCtrl.Instance;
		m_MyFan = MyFanCtrl.Instance;
		m_RGBLB = MyRgbLightbarCtrl.Instance;
		m_MySetting = new MySettingCtrl();
		m_Osd = new OSDManager();
		rgbkeyboard = RGBKeyboard.Instance;
		hidrgblightbar = HIDRGBLightbar.Instance;
		ApplicationNames = new List<string> { "MyRGBKeyboard", "MySystem", "MyFan", "MySetting", "MyRgbLightbar", "MyTouchPad" };
		FirstTimeDefaultTool();
		if (e.Args.Count() == 0)
		{
			if (m_MQTTService == null)
			{
				LogCtrl.TraceMessage("m_MQTTService==null, then create MqttClientCtrl.Instance.", "Application_Startup", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 133);
				m_MQTTService = MqttClientCtrl.Instance;
			}
			if (m_MQTTService != null)
			{
				m_MQTTService.ClientMessage += M_MQTTService_ClientMessage;
				m_MQTTService.ClientConnection += M_MQTTService_ClientConnection;
				m_MQTTService.Run();
				LogCtrl.TraceMessage("m_MQTTService!=null, running.", "Application_Startup", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 141);
			}
			else
			{
				LogCtrl.TraceMessage("m_MQTTService==null, do nothing.", "Application_Startup", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 145);
			}
			return;
		}
		m_MQTTService.ClientMessage -= M_MQTTService_ClientMessage;
		m_MQTTService.ClientConnection -= M_MQTTService_ClientConnection;
		Arguments.Uninstall = e.Args.Contains("-u");
		if (Arguments.Uninstall)
		{
			LogCtrl.TraceMessage("Uninstall", "Application_Startup", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 161);
			KillProcess("GamingCenterU");
			KillProcess("ControlCenterU");
			KillProcess("CreatorCenter");
			KillProcess("CreatorTray");
			KillProcess("SystrayComponent");
			LogCtrl.Write("[Application_Startup] Set_APExistToEC 0");
			EcCtrl.Set_APExistToEC(bExist: false);
			rgbkeyboard.init();
			rgbkeyboard.Uninstall();
			m_MyFan?.Uninstall();
			m_MySetting.Uninstall();
			BatteryProtection2.Instance.Uninstall();
		}
		if (host != null)
		{
			host.CloseConnect();
		}
		Application.Current.Shutdown();
	}

	private void M_MQTTService_ClientConnection(string connectMessage)
	{
		if (connectMessage == "Connection")
		{
			StartMainWork();
			return;
		}
		Application.Current.Dispatcher.Invoke(delegate
		{
			Application.Current.Shutdown();
		});
	}

	private void M_MQTTService_ClientMessage(string topic, MqttMsgPublishEventArgs e)
	{
		Recieve(e.Topic, e.Message);
	}

	public static void Recieve(string topic, byte[] Message)
	{
		try
		{
			switch (topic)
			{
			case "Display/Control":
				MyDisplay_Manager.Instance.Receive(Message);
				break;
			case "ProcessControl/Control":
				ProcessControl.Instance.Receive(Message);
				break;
			case "BatteryProtection/Control":
				BatteryProtection2.Instance.Receive(Message);
				break;
			case "Openvino/Control":
				OpenvinoManager.Receive(Message);
				break;
			case "System/Control":
				m_MySystem?.Receive(Message);
				break;
			case "Customize/Control":
				CustomizeCtrl.Receive(Message);
				break;
			case "Fan/Control":
				MyFanCtrl.Instance.Receive(Message);
				break;
			case "Setting/Control":
				if (m_MySetting != null)
				{
					m_MySetting.Recieve(Message);
				}
				break;
			case "MyRgbLightbar/Control":
				if (bDebug)
				{
					CustomizeInfo.m_sLightbarType = "2";
				}
				if (CustomizeInfo.m_sLightbarType == "2")
				{
					MyRgbLightbarCtrl.Instance.Recieve(Message);
				}
				break;
			case "Keyboard/Ctrl":
				if (RGBKeyboard.Instance != null)
				{
					RGBKeyboard.Instance.OnMqttMessage(topic, Encoding.UTF8.GetString(Message));
				}
				break;
			case "HidLightbar/Ctrl":
				if (HIDRGBLightbar.Instance != null)
				{
					HIDRGBLightbar.Instance.OnMqttMessage(topic, Encoding.UTF8.GetString(Message));
				}
				break;
			case "Service/Close":
				LogCtrl.Write("[M_MQTTService_ClientMessage] Service_Close");
				Application.Current.Dispatcher.Invoke(delegate
				{
					Application.Current.Shutdown();
				});
				break;
			case "Languages/Control":
				m_Osd?.Recieve(Message);
				break;
			case "Service/Ctrl":
				ServiceRecieve(Message);
				break;
			}
		}
		catch (Exception)
		{
		}
	}

	private void Application_Exit(object sender, ExitEventArgs e)
	{
		Task.Run(delegate
		{
			LogCtrl.Write("[Application_Exit] 停止 WMIReceiveEvent");
			m_Wmi.EndWMIRecieveEvent();
			NvramVariable.UpdateBufToFwVars();
			LogCtrl.Write("[Application_Exit] Disable MySystem");
			m_MySystem?.Dispose();
			LogCtrl.Write("[Application_Exit] Disable BatteryProtection2");
			BatteryProtection2.Instance.Disable();
		});
		int num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "ServiceReady", 0, RegistryValueKind.DWord);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "ServiceReady", 0, RegistryValueKind.DWord);
		KeyboardCloseTimer.CreateInstance.Dispose();
		m_MQTTService.Disconnect();
		ApplicationReset();
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write("[Application_Exit]");
		LogCtrl.Write("Service is Ready : " + num);
		ReflashTray.RefreshTrayArea();
		if (Arguments.Uninstall)
		{
			LogCtrl.Write("[Application_Exit] Uninstall");
		}
		else if (num != 0)
		{
			LogCtrl.Write("[Application_Exit] Disable MyFan");
			m_MyFan?.DisableByService();
			LogCtrl.Write("[Application_Exit] Disable MyRgbKeyboard");
			if (rgbkeyboard != null)
			{
				rgbkeyboard?.DisableByService();
			}
			if (CustomizeInfo.m_sLightbarType == "2")
			{
				LogCtrl.Write("[Application_Exit] Disable MyRgbLightbar");
				m_RGBLB?.DisableByService();
			}
			LogCtrl.Write("[Application_Exit] Disable MySetting");
			m_MySetting?.DisableByService();
			LogCtrl.Write("[Application_Exit] Disable OSDManager");
			m_Osd?.DisableByService();
			LogCtrl.Write("[Application_Exit] Set_APExistToEC");
			EcCtrl.Set_APExistToEC(bExist: false);
			LogCtrl.Write("[Application_Exit] Unload EC");
			EcCtrl.UnloadDrv();
		}
	}

	private void InitalizeStartPerparation()
	{
		LogCtrl.Write("[InitalizeStartPerparation]");
		LogCtrl.Write("[InitalizeStartPerparation] InitFanTable " + DateTime.Now.ToString());
		if (m_MyFanTable != null)
		{
			m_MyFanTable.FanTable_Init();
		}
		LogCtrl.Write("[InitalizeStartPerparation] Set_APExistToEC");
		EcCtrl.Set_APExistToEC(bExist: true);
		CustomizeCtrl.Init();
		WKD_CriticalBatterySetting.HardCodeLevel();
		LogCtrl.Write("[InitalizeStartPerparation] KeyBoardType: " + CustomizeInfo.m_sKeyboardType.ToString());
		if (bDebug)
		{
			CustomizeInfo.m_sLightbarType = "2";
		}
		LogCtrl.Write("[InitalizeStartPerparation] LightbarType: " + CustomizeInfo.m_sLightbarType.ToString());
		LogCtrl.Write("[InitalizeStartPerparation] Get ACLineStatus");
		m_PowerModeEvent?.RefreshACLineStatus();
		LogCtrl.Write("[InitalizeStartPerparation] 開啟 WMIReceiveEvent for 監聽 EC scancode");
		m_Wmi.StartWMIReceiveEvent(m_Wmi.WMIHandleEvent);
		LogCtrl.Write("[InitalizeStartPerparation] 開啟 PowerModeChanged Events");
		SystemEvents.PowerModeChanged += m_PowerModeEvent.Changed;
		ModernStandbyEvent createInstance = ModernStandbyEvent.CreateInstance;
		createInstance.dispatcher = base.Dispatcher;
		createInstance.MonitorMondernStandBy();
		createInstance.ModernStandbyChanged += ModernStandbyChangedEventHandler;
		LogCtrl.Write("[InitalizeStartPerparation] Realtek Registry clear on fisrt time");
		try
		{
			RealtekWDK instance = RealtekWDK.Instance;
			if (!instance.AuditMode())
			{
				if (instance.GetClearValue() == 1)
				{
					instance.ClearRealtekReg();
					instance.SetclearValue(0);
				}
			}
			else
			{
				instance.ClearRealtekReg();
				instance.SetclearValue(1);
			}
		}
		catch
		{
		}
	}

	private async void ModernStandbyChangedEventHandler(object status, EventArgs e)
	{
		LogCtrl.Write("ModernStandby " + status);
		if (status.ToString() == "Off")
		{
			ModernOff();
		}
		else if (status.ToString() == "On")
		{
			try
			{
				ModernOn();
			}
			catch
			{
			}
			LogCtrl.TraceMessage("Not init resume done", "ModernStandbyChangedEventHandler", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 549);
		}
	}

	private void ModernOff()
	{
		if (EcCtrl.GetProjectIdFromEC().IsProjectId_Commercial())
		{
			return;
		}
		BIOS_PROJECT_ID bios = EcCtrl.GetBiosProjctID();
		try
		{
			RGBKeyboard rgbkeyboard = RGBKeyboard.Instance;
			if (rgbkeyboard != null)
			{
				new Thread((ThreadStart)delegate
				{
					if (bios == BIOS_PROJECT_ID.IDW || bios == BIOS_PROJECT_ID.IDS)
					{
						rgbkeyboard.GetHIDKeyboard()?.NightPowerSwitch(NightPower: false);
					}
					if ((bios == BIOS_PROJECT_ID.IDX || bios == BIOS_PROJECT_ID.IDY || bios == BIOS_PROJECT_ID.IDP) && rgbkeyboard.GetHIDKeyboard() != null)
					{
						HIDKeyboard hIDKeyboard = rgbkeyboard.GetHIDKeyboard();
						if (hIDKeyboard != null && hIDKeyboard._KeyboardControl.ILM_RGBKB_GetRGBKeyboardType() == RGBKB_Type.FourZone)
						{
							rgbkeyboard.GetHIDKeyboard()._KeyboardControl.StopMusicTransfer();
						}
					}
					if (bios == BIOS_PROJECT_ID.IDX || bios == BIOS_PROJECT_ID.IDY || bios == BIOS_PROJECT_ID.IDP || bios == BIOS_PROJECT_ID.IDW || bios == BIOS_PROJECT_ID.IDS)
					{
						rgbkeyboard.GetHIDKeyboard()?._KeyboardControl.HID_Set_Effect_Type_08H(1, 0, 0, 0, 0, 0, 0);
					}
				}).Start();
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write(ex.ToString());
		}
		try
		{
			new Thread((ThreadStart)delegate
			{
				if (CustomizeInfo.m_sLightbarType == "2")
				{
					MyRgbLightbarCtrl.Instance.OnModernStandby();
				}
			}).Start();
		}
		catch (Exception ex2)
		{
			LogCtrl.Write(ex2.ToString());
		}
		try
		{
			LogCtrl.Write("BIOS_PROJECT_ID: " + bios);
			if (bios != BIOS_PROJECT_ID.IDY && bios != BIOS_PROJECT_ID.IDP && bios != BIOS_PROJECT_ID.IDM)
			{
				return;
			}
			HIDRGBLightbar hidLightbar = HIDRGBLightbar.Instance;
			if (hidLightbar != null)
			{
				new Thread((ThreadStart)delegate
				{
					hidLightbar.GetHIDLightbar()?._KeyboardControl.HID_Set_Effect_Type_08H(1, 0, 0, 0, 0, 0, 0);
				}).Start();
			}
		}
		catch (Exception ex3)
		{
			LogCtrl.Write(ex3.ToString());
		}
	}

	private async void ModernOn()
	{
		m_PowerModeEvent?.RefreshACLineStatus();
		LogCtrl.TraceMessage("Set_APExistToEC", "ModernOn", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 643);
		EcCtrl.Set_APExistToEC(bExist: true);
		LogCtrl.TraceMessage("Resume MyFan", "ModernOn", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 646);
		m_MyFan.Resume();
		if (CustomizeInfo.m_sLightbarType == "2")
		{
			LogCtrl.TraceMessage("Resume MyRgbLightbar", "ModernOn", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 652);
			MyRgbLightbarCtrl.Instance.Resume();
		}
		LogCtrl.TraceMessage("Resume  HIDKeyboard  start " + DateTime.Now.ToString(), "ModernOn", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 657);
		await Task.Run(async delegate
		{
			for (int i = 0; i < 5; i++)
			{
				RGBKeyboard instance = RGBKeyboard.Instance;
				RGBKeyboard.m_LM = null;
				instance.init();
				LogCtrl.Write("KB Fw Version : " + RGBKeyboard.m_LM?.LM_GetFirmwareVersion());
				string text = RGBKeyboard.m_LM?.LM_GetFirmwareVersion();
				if (instance.GetHIDKeyboard() != null && text != "0.0.0.0" && text != "")
				{
					instance.Resume();
					break;
				}
				await Task.Delay(1000);
				LogCtrl.TraceMessage("Resume HIDKeyboard " + i + "0 seconds ", "ModernOn", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 677);
			}
		});
		LogCtrl.TraceMessage("Resume  HidLightbar  start " + DateTime.Now.ToString(), "ModernOn", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 681);
		await Task.Run(async delegate
		{
			for (int i = 0; i < 5; i++)
			{
				HIDRGBLightbar instance = HIDRGBLightbar.Instance;
				HIDRGBLightbar.m_LB = null;
				hidrgblightbar.init();
				LogCtrl.Write("LB Fw Version : " + HIDRGBLightbar.m_LB?.LM_GetFirmwareVersion());
				string text = HIDRGBLightbar.m_LB?.LM_GetFirmwareVersion();
				if (hidrgblightbar.GetHIDLightbar() != null && text != "0.0.0.0" && text != "")
				{
					instance.Resume();
					break;
				}
				await Task.Delay(1000);
				LogCtrl.TraceMessage("Resume HidLightbar " + i + "0 seconds ", "ModernOn", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 700);
			}
		});
		LogCtrl.TraceMessage("Resume MySetting", "ModernOn", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 705);
		m_MySetting.Resume();
		LogCtrl.TraceMessage("Resume BatteryProection", "ModernOn", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 708);
		BatteryProtection2.Instance.Resume();
		ReflashTray.RefreshTrayArea();
	}

	private void StartMainWork()
	{
		sw.Reset();
		sw.Restart();
		InitalizeStartPerparation();
		sw.Stop();
		LogCtrl.TraceMessage("Perparation: " + sw.ElapsedMilliseconds + " ms", "StartMainWork", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 723);
		foreach (string applicationName in ApplicationNames)
		{
			TasksMoniter.Add(applicationName, null);
		}
		Task.Run(delegate
		{
			while (true)
			{
				for (int i = 0; i < TasksMoniter.Count; i++)
				{
					KeyValuePair<string, Task> keyValuePair = TasksMoniter.ElementAt(i);
					Task task = StartUpTask(keyValuePair.Key, keyValuePair.Value);
					if (task != null)
					{
						TasksMoniter[keyValuePair.Key] = task;
					}
				}
				Thread.Sleep(30000);
			}
		});
		Thread.Sleep(3000);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath + "\\ItemSupport", "ServiceReady", 1, RegistryValueKind.DWord);
	}

	private Task StartUpTask(string ApplicationName, Task taskX)
	{
		if (taskX == null || !taskX.IsCompleted)
		{
			return ApplicationName switch
			{
				"MyRGBKeyboard" => Task.Run(delegate
				{
					LogCtrl.Write("[StartUpTask] Enable RGBLightKeyboard ");
					rgbkeyboard.init();
					rgbkeyboard.EnableByService();
					hidrgblightbar.init();
					hidrgblightbar.EnableByService();
					CheckAurora.Instance.SetDispatcher(base.Dispatcher);
				}), 
				"MySystem" => Task.Run(delegate
				{
					m_MQTTService.ClientMessage += M_MQTTService_ClientMessage1;
					_ = ProcessControl.Instance;
					LogCtrl.Write("[StartUpTask] Enable MySystem");
					m_MySystem.DisableByService();
					LogCtrl.Write("[StartUpTask] Enable BatteryProtection2");
					BatteryProtection2.Instance.EnableByService();
					return "Enable MySystem";
				}), 
				"MyFan" => Task.Run(delegate
				{
					LogCtrl.Write("[StartUpTask] Enable MyFan");
					m_MyFan.EnableByService(base.Dispatcher);
					return "Enable MyFan";
				}), 
				"MySetting" => Task.Run(delegate
				{
					RealtekWDK.Instance.StartCalibration();
					KeyboardCloseTimer.CreateInstance.SetDispatcher(base.Dispatcher);
					LogCtrl.Write("[StartUpTask] Enable MySetting");
					m_MySetting.EnableByService();
					return "Enable MySetting";
				}), 
				"MyRgbLightbar" => Task.Run(delegate
				{
					if (CustomizeInfo.m_sLightbarType == "2")
					{
						LogCtrl.Write("[StartUpTask] Enable MyRgbLightbar");
						m_RGBLB.EnableByService();
					}
					return "Enable MyRgbLight";
				}), 
				_ => null, 
			};
		}
		if (taskX.Exception != null)
		{
			Console.WriteLine(ApplicationName + " Task is restart");
			LogCtrl.Write("[StartUpTask] task exception " + taskX.Exception.ToString());
			LogCtrl.Write("[StartUpTask] " + ApplicationName + " Task is restart ");
			taskX.Dispose();
			taskX = null;
		}
		else
		{
			Console.WriteLine("***** {0} still running *****", ApplicationName);
		}
		return null;
	}

	private void M_MQTTService_ClientMessage1(string topic, MqttMsgPublishEventArgs e)
	{
		if (topic == "Power/Shutdown")
		{
			LogCtrl.Write("Power Shutdown");
		}
	}

	public void ApplicationReset()
	{
		bIsExit = true;
		for (int i = 0; i < TasksMoniter.Count; i++)
		{
			if (TasksMoniter.Keys.Contains(TasksMoniter.ElementAt(i).Key))
			{
				TasksMoniter[TasksMoniter.ElementAt(i).Key] = null;
			}
		}
		TasksMoniter.Clear();
	}

	private void KillProcess(string processName)
	{
		try
		{
			Process[] processesByName = Process.GetProcessesByName(processName);
			for (int i = 0; i < processesByName.Count(); i++)
			{
				processesByName[i].Kill();
				LogCtrl.Write($"KillProcess {processName}");
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"KillProcess {processName} Failed {ex.ToString()}");
		}
	}

	public static async void ServiceRecieve(byte[] data)
	{
		string text = ((dynamic)(await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data))))["Action"];
		_ = string.Empty;
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write("App | Receive | msg = " + text);
		if (text == "RESTORE")
		{
			MyFanCtrl.Instance.Restore();
			MyRgbLightbarCtrl.Instance.Restore();
			RGBKeyboard.Instance.Restore();
			m_MySetting.Restore();
		}
	}

	private void FirstTimeDefaultTool()
	{
		CustomizeInfo.m_ProjectID = EcCtrl.GetProjectIdFromEC().ToString();
		LogCtrl.Write("m_ProjectID: " + CustomizeInfo.m_ProjectID);
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "ProjectID", CustomizeInfo.m_ProjectID, RegistryValueKind.DWord);
		try
		{
			m_FirstTime = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "FirstTime", 0);
			LogCtrl.Write("m_FirstTime: " + m_FirstTime);
			if (m_FirstTime == 1)
			{
				m_FirstTime = 0;
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2", "FirstTime", m_FirstTime, RegistryValueKind.DWord);
				int customizeTarget = RegistryCtrl.GetCustomizeTarget();
				string text = new FileInfo(Assembly.GetExecutingAssembly().Location).Directory.Parent.Parent.FullName + "\\DefaultTool";
				LogCtrl.Write("DefaultToolDir : " + text);
				Process process = new Process();
				ProcessStartInfo processStartInfo = new ProcessStartInfo
				{
					WindowStyle = ProcessWindowStyle.Hidden,
					FileName = text + "\\DefaultTool.exe"
				};
				process.StartInfo = processStartInfo;
				processStartInfo.Arguments = customizeTarget + " -i";
				processStartInfo.RedirectStandardOutput = true;
				processStartInfo.WorkingDirectory = text;
				process.StartInfo.UseShellExecute = false;
				process.StartInfo.CreateNoWindow = true;
				process.Start();
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("First time DefaultTool exception: " + ex, "FirstTimeDefaultTool", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\App.xaml.cs", 1182);
		}
	}

	private void LaunchAllPlugins()
	{
		try
		{
			string text = "\\OEM\\Plugin\\";
			string text2 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, text, "Path", "");
			string[] array = RegistryCtrl.RegistrySoftwareKeyGet(RegistryHive.LocalMachine, text);
			foreach (string text3 in array)
			{
				string text4 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, text + "\\" + text3, "AppName", "") + ".exe";
				if (File.Exists(text2 + "\\" + text3.ToString() + "\\" + text4))
				{
					Process[] processesByName = Process.GetProcessesByName(text3.ToString());
					for (int j = 0; j < processesByName.Count(); j++)
					{
						processesByName[j].Kill();
					}
					try
					{
						Process.Start(new ProcessStartInfo
						{
							WindowStyle = ProcessWindowStyle.Hidden,
							FileName = text4,
							WorkingDirectory = text2 + "\\" + text3.ToString()
						});
					}
					catch (Exception ex)
					{
						Console.WriteLine("LaunchAllPlugins | Process Start Exception: " + ex.Message);
					}
				}
				else
				{
					Console.WriteLine("LaunchAllPlugins | " + text4 + " is not found.");
				}
			}
		}
		catch (Exception ex2)
		{
			Console.WriteLine("LaunchAllPlugins | RegistrySoftwareKeyGet Exception: " + ex2.Message);
		}
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
	public void InitializeComponent()
	{
		if (!_contentLoaded)
		{
			_contentLoaded = true;
			base.Startup += Application_Startup;
			base.Exit += Application_Exit;
			Uri resourceLocator = new Uri("/GCUService;component/app.xaml", UriKind.Relative);
			Application.LoadComponent(this, resourceLocator);
		}
	}

	[STAThread]
	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
	public static void Main()
	{
		App app = new App();
		app.InitializeComponent();
		app.Run();
	}
}
