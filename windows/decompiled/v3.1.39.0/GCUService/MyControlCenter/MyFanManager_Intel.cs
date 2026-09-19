using System;
using System.Diagnostics;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Threading;
using Define;
using Microsoft.Win32;
using MyControlCenter.MyFan.FanTable;
using MyECIO;
using RegistryUtils;
using Utility;

namespace MyControlCenter;

public class MyFanManager_Intel : MyFanManager
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private string m_RegistryPath = "\\OEM\\GamingCenter2\\MyFanManager_Intel";

	private string className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	public uint m_CurrentIndex = 2u;

	public uint m_SysPowerModeIndex = 2u;

	public uint m_SysPowerModeIndex_DC = 3u;

	private uint m_nDefaultPowerMode = 2u;

	private uint m_nDefaultPowerMode_DC = 3u;

	public uint m_BenchmarkMode;

	private int m_nBenchmarkModeSupport = 1;

	private uint m_CpuMode = 2u;

	private uint GamingMode_PL1_Default;

	private uint GamingMode_PL2_Default;

	private uint GamingMode_PL4_Default;

	private uint GamingMode_Tau_Default = 56u;

	private uint OfficeMode_PL1_Default = 5u;

	private uint OfficeMode_PL2_Default = 5u;

	private uint OfficeMode_PL4_Default = 5u;

	private uint OfficeMode_Tau_Default = 56u;

	private uint BatterySaver_PL1_Default = 5u;

	private uint BatterySaver_PL2_Default = 5u;

	private uint BatterySaver_PL4_Default = 5u;

	private uint m_DGpuMode = 2u;

	public new uint g_FanMode = 1u;

	public new uint g_FanEnhanced;

	private FanOfficeAdvLvPwms AdvL1Pwms = new FanOfficeAdvLvPwms();

	private FanOfficeAdvLvPwms AdvL2Pwms = new FanOfficeAdvLvPwms();

	private FanOfficeAdvLvPwms AdvL3Pwms = new FanOfficeAdvLvPwms();

	private int m_HiddenFanQuietMode;

	private FanTable_Manager m_FanTableManager = new FanTable_Manager();

	private int[] DefaultPWM = new int[5];

	private int g_PowerMode;

	public new int g_DefaultMode;

	public new int g_SupportMyFan3 = 1;

	private new int g_TurboModeSupport;

	public new int g_TurboLevelSupport;

	public new uint g_QkeyDefine;

	public new int g_MyFan3p5Flag;

	private DefaultProfileInfo cDefaultProfile1 = new DefaultProfileInfo();

	private DefaultProfileInfo cDefaultProfile2 = new DefaultProfileInfo();

	private DefaultProfileInfo cDefaultProfile3 = new DefaultProfileInfo();

	private RegistryMonitor registryMonitor;

	private bool bFocusCPUPowerModeByUser;

	private bool bStartPowerPlanMonitor;

	private int m_FanTableDelayTime = 150;

	private Dispatcher _dispatcher;

	private object _PStateHandler = new object();

	private bool _PStateWorker = true;

	private Stopwatch sw = new Stopwatch();

	private Stopwatch pressSw = new Stopwatch();

	private int _SateDelay = 5000;

	private bool PressLock = true;

	private uint PressG;

	private uint LastG;

	private SemaphoreSlim FansemporeSlim = new SemaphoreSlim(1, 1);

	private Stopwatch stopwatch = new Stopwatch();

	private uint LastCommand;

	private SemaphoreSlim FansemporeSlim2 = new SemaphoreSlim(1, 1);

	private Stopwatch stopwatch2 = new Stopwatch();

	private uint LastCommand2;

	private void SetDispatcher(Dispatcher dispatcher)
	{
		_dispatcher = dispatcher;
	}

	public override int GetTurboModeSupportFlag()
	{
		return g_TurboModeSupport;
	}

	public override void EnableByService(Dispatcher dispatcher = null)
	{
		SetDispatcher(dispatcher);
		IsSupportMyFan3();
		CheckMyFan3p5Flag();
		g_QkeyDefine = GetQkeyDefine();
		g_PowerMode = PowerModeEvent.g_ACLineStatus;
		LoadRegistry();
		_ = m_BenchmarkMode;
		Init();
	}

	public override void Disable()
	{
	}

	public override async void Receive(byte[] data)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(data));
		string text = Convert.ToString(val["Action"]);
		LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
		LogCtrl.Write(className + "[Receive] Action = " + text);
		switch (text)
		{
		case "GETSTATUS":
			UpdateStatusToClient(1);
			break;
		case "DEFAULT":
			UserSet_Default();
			UpdateStatusToClient(1);
			break;
		case "SYSPOWER_PERFORMANCE_MODE":
			SetSysPowerMode1(text, val);
			UpdateStatusToClient(1);
			break;
		case "SYSPOWER_BALANCED_MODE":
			SetSysPowerMode2(text, val);
			UpdateStatusToClient(1);
			break;
		case "SYSPOWER_BATTERYSAVER_MODE":
			SetSysPowerMode3(text, val);
			UpdateStatusToClient(1);
			break;
		case "SYSPOWER_PERFORMANCE_SETTING":
		case "SYSPOWER_BALANCED_SETTING":
		case "SYSPOWER_BATTERYSAVER_SETTING":
			UserSet_SysPowerMode_Setting(text, val);
			UpdateStatusToClient(1);
			break;
		case "BENCHMARK_ON":
		case "BENCHMARK_OFF":
			UserSet_Benchmark(text);
			UpdateStatusToClient(1);
			break;
		case "GET_FAN_SPEED_CURVE_SETTING":
			UserGet_FanSpeedCurveSetting(val);
			break;
		case "SET_FAN_SPEED_CURVE_SETTING":
			UserSet_FanSpeedCurveSetting(val);
			break;
		case "RESTORE_FAN_SPEED_CURVE_SETTING":
			UserSet_RestoreFanSpeedCurveSetting(val);
			break;
		case "SET_FAN_MODE_TABLE":
		{
			string text2 = Convert.ToString(val["FanMode"]);
			int millisecondsTimeout = int.Parse(Convert.ToString(val["DelayTime"]));
			uint fanMode = 1u;
			switch (text2)
			{
			case "F1":
				fanMode = 1u;
				break;
			case "F2":
				fanMode = 2u;
				break;
			case "F3":
				fanMode = 3u;
				break;
			}
			SetFanMode(fanMode);
			Thread.Sleep(millisecondsTimeout);
			SetFanTableThread(fanMode, g_PowerMode);
			break;
		}
		case "SET_FAN_MODE_DELAYTIME":
			m_FanTableDelayTime = int.Parse(Convert.ToString(val["DelayTime"]));
			break;
		}
	}

	public override void UpdateStatusToClient(int autosave, int cpuusage = 0, int cputemp = 0, bool updateOperationMode = true)
	{
		if (autosave != 0)
		{
			var data = new
			{
				SysPowerModeIndex = m_SysPowerModeIndex.ToString(),
				SysPowerModeIndex_DC = m_SysPowerModeIndex_DC.ToString(),
				Profile1_P = cDefaultProfile1.P.ToString(),
				Profile1_G = cDefaultProfile1.G.ToString(),
				Profile1_F = cDefaultProfile1.F.ToString(),
				Profile2_P = cDefaultProfile2.P.ToString(),
				Profile2_G = cDefaultProfile2.G.ToString(),
				Profile2_F = cDefaultProfile2.F.ToString(),
				Profile3_P = cDefaultProfile3.P.ToString(),
				Profile3_G = cDefaultProfile3.G.ToString(),
				Profile3_F = cDefaultProfile3.F.ToString(),
				Profile1_P_DC = cDefaultProfile1.P_DC.ToString(),
				Profile1_G_DC = cDefaultProfile1.G_DC.ToString(),
				Profile1_F_DC = cDefaultProfile1.F_DC.ToString(),
				Profile2_P_DC = cDefaultProfile2.P_DC.ToString(),
				Profile2_G_DC = cDefaultProfile2.G_DC.ToString(),
				Profile2_F_DC = cDefaultProfile2.F_DC.ToString(),
				Profile3_P_DC = cDefaultProfile3.P_DC.ToString(),
				Profile3_G_DC = cDefaultProfile3.G_DC.ToString(),
				Profile3_F_DC = cDefaultProfile3.F_DC.ToString(),
				Benchmark = m_BenchmarkMode.ToString(),
				HiddenFanQuietMode = m_HiddenFanQuietMode.ToString(),
				ACLINESTATUS = PowerModeEvent.g_ACLineStatus.ToString()
			};
			App.m_MQTTService.Publish("Fan/Status", data, retain: false);
		}
	}

	public override void Resume()
	{
		g_PowerMode = PowerModeEvent.g_ACLineStatus;
		LoadRegistry();
		_ = m_BenchmarkMode;
		Init();
	}

	public override void OnModernStandby()
	{
	}

	public override void PowerStatusChange(int mode)
	{
		g_PowerMode = mode;
		switch (mode)
		{
		case 0:
			LogCtrl.Write(className + "[PowerModeChanged] DC Mode");
			m_CurrentIndex = m_SysPowerModeIndex_DC;
			break;
		case 1:
			LogCtrl.Write(className + "[PowerModeChanged] AC Mode");
			m_CurrentIndex = m_SysPowerModeIndex;
			break;
		}
		Init();
	}

	public override void Uninstall()
	{
		SetApExist(exist: false);
	}

	public override void Restore()
	{
		LoadDefault();
		Init();
	}

	public override void ModeSwitchChanged()
	{
		if (m_BenchmarkMode == 1)
		{
			return;
		}
		uint num = 1u;
		if (PowerModeEvent.g_ACLineStatus == 1)
		{
			switch (m_SysPowerModeIndex)
			{
			case 1u:
				num = 2u;
				App.m_Osd.SendOsdModeToClient(num);
				UserSet_Mode2();
				break;
			case 2u:
				num = 3u;
				App.m_Osd.SendOsdModeToClient(num);
				UserSet_Mode3();
				break;
			case 3u:
				num = 1u;
				App.m_Osd.SendOsdModeToClient(num);
				UserSet_Mode1();
				break;
			}
		}
		else
		{
			switch (m_SysPowerModeIndex_DC)
			{
			case 1u:
				num = 2u;
				App.m_Osd.SendOsdModeToClient(num);
				UserSet_Mode2();
				break;
			case 2u:
				num = 3u;
				App.m_Osd.SendOsdModeToClient(num);
				UserSet_Mode3();
				break;
			case 3u:
				num = 1u;
				App.m_Osd.SendOsdModeToClient(num);
				UserSet_Mode1();
				break;
			}
		}
		UpdateStatusToClient(1);
	}

	public override void FanBoostUpdate()
	{
		if (g_SupportMyFan3 == 1 && g_QkeyDefine == 1)
		{
			App.m_Osd.SetOsdWay(167);
		}
	}

	public void SetSysPowerMode1(string action, dynamic data)
	{
		try
		{
			if (Convert.ToString(data["Page"]) == "AC")
			{
				m_SysPowerModeIndex = 1u;
				SetRegistry("SysPowerModeIndex", m_SysPowerModeIndex);
				if (g_PowerMode == 1)
				{
					m_CurrentIndex = m_SysPowerModeIndex;
					m_CpuMode = cDefaultProfile1.P;
					m_DGpuMode = cDefaultProfile1.G;
					g_FanMode = cDefaultProfile1.F;
					SetSysPowerModeActive(m_CurrentIndex, m_CpuMode, m_DGpuMode, g_FanMode);
				}
			}
			else
			{
				m_SysPowerModeIndex_DC = 1u;
				SetRegistry("SysPowerModeIndex_DC", m_SysPowerModeIndex_DC);
				if (g_PowerMode == 0)
				{
					m_CurrentIndex = m_SysPowerModeIndex_DC;
					m_CpuMode = cDefaultProfile1.P_DC;
					m_DGpuMode = cDefaultProfile1.G_DC;
					g_FanMode = cDefaultProfile1.F_DC;
					SetSysPowerModeActive(m_CurrentIndex, m_CpuMode, m_DGpuMode, g_FanMode);
				}
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write(className + "[SetSysPowerMode1] Exception" + ex.Message);
		}
	}

	public void SetSysPowerMode2(string action, dynamic data)
	{
		try
		{
			if (Convert.ToString(data["Page"]) == "AC")
			{
				m_SysPowerModeIndex = 2u;
				SetRegistry("SysPowerModeIndex", m_SysPowerModeIndex);
				if (g_PowerMode == 1)
				{
					m_CurrentIndex = m_SysPowerModeIndex;
					m_CpuMode = cDefaultProfile2.P;
					m_DGpuMode = cDefaultProfile2.G;
					g_FanMode = cDefaultProfile2.F;
					SetSysPowerModeActive(m_CurrentIndex, m_CpuMode, m_DGpuMode, g_FanMode);
				}
			}
			else
			{
				m_SysPowerModeIndex_DC = 2u;
				SetRegistry("SysPowerModeIndex_DC", m_SysPowerModeIndex_DC);
				if (g_PowerMode == 0)
				{
					m_CurrentIndex = m_SysPowerModeIndex_DC;
					m_CpuMode = cDefaultProfile2.P_DC;
					m_DGpuMode = cDefaultProfile2.G_DC;
					g_FanMode = cDefaultProfile2.F_DC;
					SetSysPowerModeActive(m_CurrentIndex, m_CpuMode, m_DGpuMode, g_FanMode);
				}
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write(className + "[SetSysPowerMode2] Exception" + ex.Message);
		}
	}

	public void SetSysPowerMode3(string action, dynamic data)
	{
		try
		{
			if (Convert.ToString(data["Page"]) == "AC")
			{
				m_SysPowerModeIndex = 3u;
				SetRegistry("SysPowerModeIndex", m_SysPowerModeIndex);
				if (g_PowerMode == 1)
				{
					m_CurrentIndex = m_SysPowerModeIndex;
					m_CpuMode = cDefaultProfile3.P;
					m_DGpuMode = cDefaultProfile3.G;
					g_FanMode = cDefaultProfile3.F;
					SetSysPowerModeActive(m_CurrentIndex, m_CpuMode, m_DGpuMode, g_FanMode);
				}
			}
			else
			{
				m_SysPowerModeIndex_DC = 3u;
				SetRegistry("SysPowerModeIndex_DC", m_SysPowerModeIndex_DC);
				if (g_PowerMode == 0)
				{
					m_CurrentIndex = m_SysPowerModeIndex_DC;
					m_CpuMode = cDefaultProfile3.P_DC;
					m_DGpuMode = cDefaultProfile3.G_DC;
					g_FanMode = cDefaultProfile3.F_DC;
					SetSysPowerModeActive(m_CurrentIndex, m_CpuMode, m_DGpuMode, g_FanMode);
				}
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write(className + "[SetSysPowerMode3] Exception" + ex.Message);
		}
	}

	private void SetSysPowerModeActive(uint index, uint P, uint G, uint F)
	{
		SetSysPowerModeIndex(index);
		SetCpuMode(P);
		SetDGpuModeWithOverBoost(P, G, F);
		SetFanMode(F);
	}

	public override void UserSet_Mode1()
	{
		if (g_PowerMode == 1)
		{
			m_SysPowerModeIndex = 1u;
			SetRegistry("SysPowerModeIndex", m_SysPowerModeIndex);
			m_CurrentIndex = 1u;
			m_CpuMode = cDefaultProfile1.P;
			m_DGpuMode = cDefaultProfile1.G;
			g_FanMode = cDefaultProfile1.F;
		}
		else
		{
			m_SysPowerModeIndex_DC = 1u;
			SetRegistry("SysPowerModeIndex_DC", m_SysPowerModeIndex_DC);
			m_CurrentIndex = 1u;
			m_CpuMode = cDefaultProfile1.P_DC;
			m_DGpuMode = cDefaultProfile1.G_DC;
			g_FanMode = cDefaultProfile1.F_DC;
		}
		SetSysPowerModeActive(m_CurrentIndex, m_CpuMode, m_DGpuMode, g_FanMode);
	}

	public override void UserSet_Mode2()
	{
		if (g_PowerMode == 1)
		{
			m_SysPowerModeIndex = 2u;
			SetRegistry("SysPowerModeIndex", m_SysPowerModeIndex);
			m_CurrentIndex = 2u;
			m_CpuMode = cDefaultProfile2.P;
			m_DGpuMode = cDefaultProfile2.G;
			g_FanMode = cDefaultProfile2.F;
		}
		else
		{
			m_SysPowerModeIndex_DC = 2u;
			SetRegistry("SysPowerModeIndex_DC", m_SysPowerModeIndex_DC);
			m_CurrentIndex = 2u;
			m_CpuMode = cDefaultProfile2.P_DC;
			m_DGpuMode = cDefaultProfile2.G_DC;
			g_FanMode = cDefaultProfile2.F_DC;
		}
		SetSysPowerModeActive(m_CurrentIndex, m_CpuMode, m_DGpuMode, g_FanMode);
	}

	public override void UserSet_Mode3()
	{
		if (g_PowerMode == 1)
		{
			m_SysPowerModeIndex = 3u;
			SetRegistry("SysPowerModeIndex", m_SysPowerModeIndex);
			m_CurrentIndex = 3u;
			m_CpuMode = cDefaultProfile3.P;
			m_DGpuMode = cDefaultProfile3.G;
			g_FanMode = cDefaultProfile3.F;
		}
		else
		{
			m_SysPowerModeIndex_DC = 3u;
			SetRegistry("SysPowerModeIndex_DC", m_SysPowerModeIndex_DC);
			m_CurrentIndex = 3u;
			m_CpuMode = cDefaultProfile3.P_DC;
			m_DGpuMode = cDefaultProfile3.G_DC;
			g_FanMode = cDefaultProfile3.F_DC;
		}
		SetSysPowerModeActive(m_CurrentIndex, m_CpuMode, m_DGpuMode, g_FanMode);
	}

	private void UserSet_Default()
	{
		Restore();
	}

	private void UserSet_SysPowerMode_Setting(string action, dynamic data)
	{
		string text = null;
		uint num = 0u;
		uint num2 = 0u;
		uint num3 = 0u;
		if (!((data["Page"] != null) ? true : false))
		{
			return;
		}
		text = Convert.ToString(data["Page"]);
		if (data["CpuMode"] != null)
		{
			switch (Convert.ToString(data["CpuMode"]))
			{
			case "P1":
				num = 1u;
				break;
			case "P2":
				num = 2u;
				break;
			case "P3":
				num = 3u;
				break;
			}
			if (num >= 1 && num <= 3)
			{
				if (text == "AC")
				{
					switch (action)
					{
					case "SYSPOWER_PERFORMANCE_SETTING":
						cDefaultProfile1.P = num;
						SetUserProfileRegistry("Index1", "P", num);
						break;
					case "SYSPOWER_BALANCED_SETTING":
						cDefaultProfile2.P = num;
						SetUserProfileRegistry("Index2", "P", num);
						break;
					case "SYSPOWER_BATTERYSAVER_SETTING":
						cDefaultProfile3.P = num;
						SetUserProfileRegistry("Index3", "P", num);
						break;
					}
				}
				else
				{
					switch (action)
					{
					case "SYSPOWER_PERFORMANCE_SETTING":
						cDefaultProfile1.P_DC = num;
						SetUserProfileRegistry("Index1", "P_DC", num);
						break;
					case "SYSPOWER_BALANCED_SETTING":
						cDefaultProfile2.P_DC = num;
						SetUserProfileRegistry("Index2", "P_DC", num);
						break;
					case "SYSPOWER_BATTERYSAVER_SETTING":
						cDefaultProfile3.P_DC = num;
						SetUserProfileRegistry("Index3", "P_DC", num);
						break;
					}
				}
			}
		}
		if (data["DGpuMode"] != null)
		{
			switch (Convert.ToString(data["DGpuMode"]))
			{
			case "G1":
				num2 = 1u;
				break;
			case "G2":
				num2 = 2u;
				break;
			case "G3":
				num2 = 3u;
				break;
			}
			if (num2 >= 1 && num2 <= 3)
			{
				if (text == "AC")
				{
					switch (action)
					{
					case "SYSPOWER_PERFORMANCE_SETTING":
						cDefaultProfile1.G = num2;
						SetUserProfileRegistry("Index1", "G", num2);
						break;
					case "SYSPOWER_BALANCED_SETTING":
						cDefaultProfile2.G = num2;
						SetUserProfileRegistry("Index2", "G", num2);
						break;
					case "SYSPOWER_BATTERYSAVER_SETTING":
						cDefaultProfile3.G = num2;
						SetUserProfileRegistry("Index3", "G", num2);
						break;
					}
				}
				else
				{
					switch (action)
					{
					case "SYSPOWER_PERFORMANCE_SETTING":
						cDefaultProfile1.G_DC = num2;
						SetUserProfileRegistry("Index1", "G_DC", num2);
						break;
					case "SYSPOWER_BALANCED_SETTING":
						cDefaultProfile2.G_DC = num2;
						SetUserProfileRegistry("Index2", "G_DC", num2);
						break;
					case "SYSPOWER_BATTERYSAVER_SETTING":
						cDefaultProfile3.G_DC = num2;
						SetUserProfileRegistry("Index3", "G_DC", num2);
						break;
					}
				}
			}
		}
		if (data["FanMode"] != null)
		{
			switch (Convert.ToString(data["FanMode"]))
			{
			case "F1":
				num3 = 1u;
				break;
			case "F2":
				num3 = 2u;
				break;
			case "F3":
				num3 = 3u;
				break;
			}
			if (num3 >= 1 && num3 <= 3)
			{
				if (text == "AC")
				{
					switch (action)
					{
					case "SYSPOWER_PERFORMANCE_SETTING":
						cDefaultProfile1.F = num3;
						SetUserProfileRegistry("Index1", "F", num3);
						break;
					case "SYSPOWER_BALANCED_SETTING":
						cDefaultProfile2.F = num3;
						SetUserProfileRegistry("Index2", "F", num3);
						break;
					case "SYSPOWER_BATTERYSAVER_SETTING":
						cDefaultProfile3.F = num3;
						SetUserProfileRegistry("Index3", "F", num3);
						break;
					}
				}
				else
				{
					switch (action)
					{
					case "SYSPOWER_PERFORMANCE_SETTING":
						cDefaultProfile1.F_DC = num3;
						SetUserProfileRegistry("Index1", "F_DC", num3);
						break;
					case "SYSPOWER_BALANCED_SETTING":
						cDefaultProfile2.F_DC = num3;
						SetUserProfileRegistry("Index2", "F_DC", num3);
						break;
					case "SYSPOWER_BATTERYSAVER_SETTING":
						cDefaultProfile3.F_DC = num3;
						SetUserProfileRegistry("Index3", "F_DC", num3);
						break;
					}
				}
			}
		}
		if (!((data["Active"] != null) ? true : false) || !(Convert.ToString(data["Active"]) == "1"))
		{
			return;
		}
		if (text == "AC" && g_PowerMode == 1)
		{
			switch (action)
			{
			case "SYSPOWER_PERFORMANCE_SETTING":
				m_SysPowerModeIndex = 1u;
				m_CpuMode = cDefaultProfile1.P;
				m_DGpuMode = cDefaultProfile1.G;
				g_FanMode = cDefaultProfile1.F;
				break;
			case "SYSPOWER_BALANCED_SETTING":
				m_SysPowerModeIndex = 2u;
				m_CpuMode = cDefaultProfile2.P;
				m_DGpuMode = cDefaultProfile2.G;
				g_FanMode = cDefaultProfile2.F;
				break;
			case "SYSPOWER_BATTERYSAVER_SETTING":
				m_SysPowerModeIndex = 3u;
				m_CpuMode = cDefaultProfile3.P;
				m_DGpuMode = cDefaultProfile3.G;
				g_FanMode = cDefaultProfile3.F;
				break;
			}
			SetRegistry("SysPowerModeIndex", m_SysPowerModeIndex);
			m_CurrentIndex = m_SysPowerModeIndex;
			SetSysPowerModeActive(m_CurrentIndex, m_CpuMode, m_DGpuMode, g_FanMode);
		}
		else if (text == "DC" && g_PowerMode == 0)
		{
			switch (action)
			{
			case "SYSPOWER_PERFORMANCE_SETTING":
				m_SysPowerModeIndex_DC = 1u;
				m_CpuMode = cDefaultProfile1.P_DC;
				m_DGpuMode = cDefaultProfile1.G_DC;
				g_FanMode = cDefaultProfile1.F_DC;
				break;
			case "SYSPOWER_BALANCED_SETTING":
				m_SysPowerModeIndex_DC = 2u;
				m_CpuMode = cDefaultProfile2.P_DC;
				m_DGpuMode = cDefaultProfile2.G_DC;
				g_FanMode = cDefaultProfile2.F_DC;
				break;
			case "SYSPOWER_BATTERYSAVER_SETTING":
				m_SysPowerModeIndex_DC = 3u;
				m_CpuMode = cDefaultProfile3.P_DC;
				m_DGpuMode = cDefaultProfile3.G_DC;
				g_FanMode = cDefaultProfile3.F_DC;
				break;
			}
			SetRegistry("SysPowerModeIndex_DC", m_SysPowerModeIndex_DC);
			m_CurrentIndex = m_SysPowerModeIndex_DC;
			SetSysPowerModeActive(m_CurrentIndex, m_CpuMode, m_DGpuMode, g_FanMode);
		}
		else
		{
			LogCtrl.Write(className + "[UserSet_SysPowerMode_Setting] Active fail, Page:" + text + ", ACLineStatus:" + g_PowerMode);
		}
	}

	private void UserSet_Benchmark(string action)
	{
		if (!(action == "BENCHMARK_ON"))
		{
			if (action == "BENCHMARK_OFF")
			{
				m_BenchmarkMode = 0u;
				SetSysPowerModeIndex(m_CurrentIndex);
				SetCpuMode(m_CpuMode);
				SetDGpuModeWithOverBoost(m_CpuMode, m_DGpuMode, g_FanMode);
				SetFanMode(g_FanMode);
			}
		}
		else
		{
			m_BenchmarkMode = 1u;
			SetSysPowerModeIndex(4u);
			SetCpuMode(4u);
			SetDGpuModeWithOverBoost(4u, 4u, 4u);
			SetFanMode(4u);
		}
		SetRegistry("BenchmarkMode", m_BenchmarkMode);
	}

	private void UserGet_FanSpeedCurveSetting(dynamic data)
	{
		try
		{
			if (!((data["FanMode"] != null && data["TableType"] != null && data["Power"] != null) ? true : false))
			{
				return;
			}
			string text = Convert.ToString(data["FanMode"]);
			string text2 = Convert.ToString(data["TableType"]);
			string text3 = Convert.ToString(data["Power"]);
			uint num = 0u;
			uint num2 = 0u;
			int num3 = -1;
			switch (text)
			{
			case "F1":
				num = 1u;
				break;
			case "F2":
				num = 2u;
				break;
			case "F3":
				num = 3u;
				break;
			}
			if (!(text2 == "CPU"))
			{
				if (text2 == "GPU")
				{
					num2 = 2u;
				}
			}
			else
			{
				num2 = 1u;
			}
			if (!(text3 == "AC"))
			{
				if (text3 == "DC")
				{
					num3 = 0;
				}
			}
			else
			{
				num3 = 1;
			}
			if (num != 0 && num2 != 0 && num3 != -1)
			{
				m_FanTableManager.GetFanTable(num, num2, num3);
			}
		}
		catch
		{
		}
	}

	private void UserSet_FanSpeedCurveSetting(dynamic data)
	{
		try
		{
			if (!((data["FanMode"] != null && data["TableType"] != null && data["Power"] != null && data["ID"] != null && data["Key"] != null && data["Value"] != null) ? true : false))
			{
				return;
			}
			string text = Convert.ToString(data["FanMode"]);
			string text2 = Convert.ToString(data["TableType"]);
			string text3 = Convert.ToString(data["Power"]);
			int id = int.Parse(Convert.ToString(data["ID"]));
			string key = Convert.ToString(data["Key"]);
			uint value = (uint)int.Parse(Convert.ToString(data["Value"]));
			uint num = 0u;
			uint num2 = 0u;
			int num3 = -1;
			switch (text)
			{
			case "F1":
				num = 1u;
				break;
			case "F2":
				num = 2u;
				break;
			case "F3":
				num = 3u;
				break;
			}
			if (!(text2 == "CPU"))
			{
				if (text2 == "GPU")
				{
					num2 = 2u;
				}
			}
			else
			{
				num2 = 1u;
			}
			if (!(text3 == "AC"))
			{
				if (text3 == "DC")
				{
					num3 = 0;
				}
			}
			else
			{
				num3 = 1;
			}
			if (num != 0 && num2 != 0 && num3 != -1)
			{
				m_FanTableManager.SetFanTableSetting(num, num2, num3, id, key, value);
			}
		}
		catch
		{
		}
	}

	private void UserSet_RestoreFanSpeedCurveSetting(dynamic data)
	{
		try
		{
			if (!((data["FanMode"] != null && data["TableType"] != null && data["Power"] != null) ? true : false))
			{
				return;
			}
			string text = Convert.ToString(data["FanMode"]);
			string text2 = Convert.ToString(data["TableType"]);
			string text3 = Convert.ToString(data["Power"]);
			uint num = 0u;
			uint num2 = 0u;
			int num3 = -1;
			switch (text)
			{
			case "F1":
				num = 1u;
				break;
			case "F2":
				num = 2u;
				break;
			case "F3":
				num = 3u;
				break;
			}
			if (!(text2 == "CPU"))
			{
				if (text2 == "GPU")
				{
					num2 = 2u;
				}
			}
			else
			{
				num2 = 1u;
			}
			if (!(text3 == "AC"))
			{
				if (text3 == "DC")
				{
					num3 = 0;
				}
			}
			else
			{
				num3 = 1;
			}
			if (num != 0 && num2 != 0 && num3 != -1)
			{
				m_FanTableManager.RestoreDefaultFanTable(num, num2, num3);
			}
		}
		catch
		{
		}
	}

	private void UserSet_FanBoost(uint mode)
	{
		g_FanEnhanced = mode;
		SetFanMode(g_FanMode);
		SetRegistry("FanEnhanced", g_FanEnhanced);
	}

	private void LoadRegistry()
	{
		int num = 0;
		int num2 = 0;
		int num3 = 0;
		int num4 = 0;
		int num5 = 0;
		int num6 = 0;
		int num7 = 0;
		int num8 = 0;
		int num9 = 0;
		int num10 = 0;
		int num11 = 0;
		int num12 = 0;
		int num13 = 0;
		int num14 = 0;
		int num15 = 0;
		int num16 = 0;
		int num17 = 0;
		int num18 = 0;
		int num19 = 0;
		int num20 = 0;
		int num21 = 0;
		try
		{
			DefaultPWM = GetFanTablePWMDefault();
			DefaultPWM = CheckFanTablePWMDefault(DefaultPWM);
			LoadOfficeAdvLvPwmsDefault();
			UpdatePLDefault_ByCheckPortId();
			num = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "SysPowerModeIndex", 2u);
			num2 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "SysPowerModeIndex_DC", 3u);
			num3 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath, "BenchmarkMode", 0);
			m_SysPowerModeIndex = (uint)num;
			m_SysPowerModeIndex_DC = (uint)num2;
			m_BenchmarkMode = (uint)num3;
			num4 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index1", "P", 1u);
			num5 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index1", "G", 1u);
			num6 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index1", "F", 1u);
			num7 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index2", "P", 2u);
			num8 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index2", "G", 2u);
			num9 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index2", "F", 2u);
			num10 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index3", "P", 3u);
			num11 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index3", "G", 3u);
			num12 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index3", "F", 3u);
			cDefaultProfile1.P = (uint)num4;
			cDefaultProfile1.G = (uint)num5;
			cDefaultProfile1.F = (uint)num6;
			cDefaultProfile2.P = (uint)num7;
			cDefaultProfile2.G = (uint)num8;
			cDefaultProfile2.F = (uint)num9;
			cDefaultProfile3.P = (uint)num10;
			cDefaultProfile3.G = (uint)num11;
			cDefaultProfile3.F = (uint)num12;
			num13 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index1", "P_DC", 1u);
			num14 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index1", "G_DC", 1u);
			num15 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index1", "F_DC", 1u);
			num16 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index2", "P_DC", 2u);
			num17 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index2", "G_DC", 2u);
			num18 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index2", "F_DC", 2u);
			num19 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index3", "P_DC", 3u);
			num20 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index3", "G_DC", 3u);
			num21 = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_RegistryPath + "\\Index3", "F_DC", 3u);
			cDefaultProfile1.P_DC = (uint)num13;
			cDefaultProfile1.G_DC = (uint)num14;
			cDefaultProfile1.F_DC = (uint)num15;
			cDefaultProfile2.P_DC = (uint)num16;
			cDefaultProfile2.G_DC = (uint)num17;
			cDefaultProfile2.F_DC = (uint)num18;
			cDefaultProfile3.P_DC = (uint)num19;
			cDefaultProfile3.G_DC = (uint)num20;
			cDefaultProfile3.F_DC = (uint)num21;
		}
		catch
		{
			LoadDefault();
		}
	}

	private void LoadDefault()
	{
		m_BenchmarkMode = 0u;
		SetRegistry("BenchmarkMode", m_BenchmarkMode);
		m_FanTableManager.RestoreDefaultFanTableAll();
		LoadDefaultPowerProfile();
		m_SysPowerModeIndex = m_nDefaultPowerMode;
		SetRegistry("SysPowerModeIndex", m_SysPowerModeIndex);
		SetUserProfileRegistry("Index1", "P", cDefaultProfile1.P);
		SetUserProfileRegistry("Index1", "G", cDefaultProfile1.G);
		SetUserProfileRegistry("Index1", "F", cDefaultProfile1.F);
		SetUserProfileRegistry("Index2", "P", cDefaultProfile2.P);
		SetUserProfileRegistry("Index2", "G", cDefaultProfile2.G);
		SetUserProfileRegistry("Index2", "F", cDefaultProfile2.F);
		SetUserProfileRegistry("Index3", "P", cDefaultProfile3.P);
		SetUserProfileRegistry("Index3", "G", cDefaultProfile3.G);
		SetUserProfileRegistry("Index3", "F", cDefaultProfile3.F);
		m_SysPowerModeIndex_DC = m_nDefaultPowerMode_DC;
		SetRegistry("SysPowerModeIndex_DC", m_SysPowerModeIndex_DC);
		SetUserProfileRegistry("Index1", "P_DC", cDefaultProfile1.P_DC);
		SetUserProfileRegistry("Index1", "G_DC", cDefaultProfile1.G_DC);
		SetUserProfileRegistry("Index1", "F_DC", cDefaultProfile1.F_DC);
		SetUserProfileRegistry("Index2", "P_DC", cDefaultProfile2.P_DC);
		SetUserProfileRegistry("Index2", "G_DC", cDefaultProfile2.G_DC);
		SetUserProfileRegistry("Index2", "F_DC", cDefaultProfile2.F_DC);
		SetUserProfileRegistry("Index3", "P_DC", cDefaultProfile3.P_DC);
		SetUserProfileRegistry("Index3", "G_DC", cDefaultProfile3.G_DC);
		SetUserProfileRegistry("Index3", "F_DC", cDefaultProfile3.F_DC);
	}

	private void LoadFeatureSupport()
	{
		try
		{
			m_nBenchmarkModeSupport = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Features", "BenchmarkModeSupport", 0);
		}
		catch (Exception ex)
		{
			LogCtrl.Write(className + "[LoadSupport] Features Exception" + ex.Message);
		}
	}

	private void LoadDefaultPowerProfile()
	{
		try
		{
			int nDefaultPowerMode = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "PowerMode", 2u);
			string obj = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "Profile1", "P1G1F1");
			string text = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "Profile2", "P2G2F2");
			string text2 = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "Profile3", "P3G3F3");
			m_nDefaultPowerMode = (uint)nDefaultPowerMode;
			string value = obj.Substring(obj.IndexOf("F") + 1, 1);
			cDefaultProfile1.F = Convert.ToUInt32(value, 16);
			value = text.Substring(text.IndexOf("F") + 1, 1);
			cDefaultProfile2.F = Convert.ToUInt32(value, 16);
			value = text2.Substring(text2.IndexOf("F") + 1, 1);
			cDefaultProfile3.F = Convert.ToUInt32(value, 16);
			value = obj.Substring(obj.IndexOf("G") + 1, 1);
			cDefaultProfile1.G = Convert.ToUInt32(value, 16);
			value = text.Substring(text.IndexOf("G") + 1, 1);
			cDefaultProfile2.G = Convert.ToUInt32(value, 16);
			value = text2.Substring(text2.IndexOf("G") + 1, 1);
			cDefaultProfile3.G = Convert.ToUInt32(value, 16);
			value = obj.Substring(obj.IndexOf("P") + 1, 1);
			cDefaultProfile1.P = Convert.ToUInt32(value, 16);
			value = text.Substring(text.IndexOf("P") + 1, 1);
			cDefaultProfile2.P = Convert.ToUInt32(value, 16);
			value = text2.Substring(text2.IndexOf("P") + 1, 1);
			cDefaultProfile3.P = Convert.ToUInt32(value, 16);
			m_nDefaultPowerMode_DC = m_nDefaultPowerMode;
			cDefaultProfile1.F_DC = cDefaultProfile1.F;
			cDefaultProfile2.F_DC = cDefaultProfile2.F;
			cDefaultProfile3.F_DC = cDefaultProfile3.F;
			cDefaultProfile1.G_DC = cDefaultProfile1.G;
			cDefaultProfile2.G_DC = cDefaultProfile2.G;
			cDefaultProfile3.G_DC = cDefaultProfile3.G;
			cDefaultProfile1.P_DC = cDefaultProfile1.P;
			cDefaultProfile2.P_DC = cDefaultProfile2.P;
			cDefaultProfile3.P_DC = cDefaultProfile3.P;
		}
		catch (Exception ex)
		{
			LogCtrl.Write(className + "[LoadPowerModeProfiles] DefaultPower Exception" + ex.Message);
			cDefaultProfile1.P = 1u;
			cDefaultProfile2.P = 2u;
			cDefaultProfile3.P = 3u;
			cDefaultProfile1.F = 1u;
			cDefaultProfile2.F = 2u;
			cDefaultProfile3.F = 3u;
			cDefaultProfile1.G = 1u;
			cDefaultProfile2.G = 2u;
			cDefaultProfile3.G = 3u;
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "PowerMode", 2u, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "Profile1", "P1G1F1", RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "Profile2", "P2G2F2", RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "Profile3", "P3G3F3", RegistryValueKind.String);
			cDefaultProfile1.P_DC = 1u;
			cDefaultProfile1.G_DC = 1u;
			cDefaultProfile1.F_DC = 1u;
			cDefaultProfile2.P_DC = 2u;
			cDefaultProfile2.G_DC = 2u;
			cDefaultProfile2.F_DC = 2u;
			cDefaultProfile3.P_DC = 3u;
			cDefaultProfile3.G_DC = 3u;
			cDefaultProfile3.F_DC = 3u;
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "PowerMode_DC", 3u, RegistryValueKind.DWord);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "Profile1_DC", "P1G1F1", RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "Profile2_DC", "P2G2F2", RegistryValueKind.String);
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\DefaultPower", "Profile3_DC", "P3G3F3", RegistryValueKind.String);
		}
	}

	private void LoadOfficeAdvLvPwmsDefault()
	{
		int t1_PWM = DefaultPWM[0] / 2;
		int num = DefaultPWM[1] / 2;
		int num2 = DefaultPWM[2] / 2;
		int num3 = DefaultPWM[3] / 2;
		int t5_PWM = DefaultPWM[4] / 2;
		AdvL1Pwms.T1_PWM = (uint)t1_PWM;
		AdvL1Pwms.T2_PWM = (uint)Math.Round((double)num * 0.9, 0, MidpointRounding.AwayFromZero);
		AdvL1Pwms.T3_PWM = (uint)Math.Round((double)num2 * 0.9, 0, MidpointRounding.AwayFromZero);
		AdvL1Pwms.T4_PWM = (uint)Math.Round((double)num3 * 0.9, 0, MidpointRounding.AwayFromZero);
		AdvL1Pwms.T5_PWM = (uint)t5_PWM;
		AdvL2Pwms.T1_PWM = (uint)t1_PWM;
		AdvL2Pwms.T2_PWM = (uint)num;
		AdvL2Pwms.T3_PWM = (uint)num2;
		AdvL2Pwms.T4_PWM = (uint)num3;
		AdvL2Pwms.T5_PWM = (uint)t5_PWM;
		AdvL3Pwms.T1_PWM = (uint)t1_PWM;
		AdvL3Pwms.T2_PWM = (uint)Math.Round((double)num * 1.1, 0, MidpointRounding.AwayFromZero);
		AdvL3Pwms.T3_PWM = (uint)Math.Round((double)num2 * 1.1, 0, MidpointRounding.AwayFromZero);
		AdvL3Pwms.T4_PWM = (uint)Math.Round((double)num3 * 1.1, 0, MidpointRounding.AwayFromZero);
		AdvL3Pwms.T5_PWM = (uint)t5_PWM;
		AdvL1Pwms = UpdateAdvPwms(AdvL1Pwms.T1_PWM, AdvL1Pwms.T2_PWM, AdvL1Pwms.T3_PWM, AdvL1Pwms.T4_PWM, AdvL1Pwms.T5_PWM);
		AdvL2Pwms = UpdateAdvPwms(AdvL2Pwms.T1_PWM, AdvL2Pwms.T2_PWM, AdvL2Pwms.T3_PWM, AdvL2Pwms.T4_PWM, AdvL2Pwms.T5_PWM);
		AdvL3Pwms = UpdateAdvPwms(AdvL3Pwms.T1_PWM, AdvL3Pwms.T2_PWM, AdvL3Pwms.T3_PWM, AdvL3Pwms.T4_PWM, AdvL3Pwms.T5_PWM);
	}

	private FanOfficeAdvLvPwms UpdateAdvPwms(uint T1_PWM, uint T2_PWM, uint T3_PWM, uint T4_PWM, uint T5_PWM)
	{
		FanOfficeAdvLvPwms fanOfficeAdvLvPwms = new FanOfficeAdvLvPwms();
		uint num = (uint)DefaultPWM[0] / 2u;
		uint num2 = (uint)DefaultPWM[4] / 2u;
		if (T1_PWM < num)
		{
			T1_PWM = num;
		}
		if (T1_PWM > num2)
		{
			T1_PWM = num2;
		}
		if (T2_PWM < num)
		{
			T2_PWM = num;
		}
		if (T2_PWM > num2)
		{
			T2_PWM = num2;
		}
		if (T3_PWM < num)
		{
			T3_PWM = num;
		}
		if (T3_PWM > num2)
		{
			T3_PWM = num2;
		}
		if (T4_PWM < num)
		{
			T4_PWM = num;
		}
		if (T4_PWM > num2)
		{
			T4_PWM = num2;
		}
		if (T5_PWM < num)
		{
			T5_PWM = num;
		}
		if (T5_PWM > num2)
		{
			T5_PWM = num2;
		}
		if (T2_PWM < T1_PWM)
		{
			T2_PWM = T1_PWM;
		}
		if (T3_PWM < T2_PWM)
		{
			T3_PWM = T2_PWM;
		}
		if (T4_PWM < T3_PWM)
		{
			T4_PWM = T3_PWM;
		}
		if (T5_PWM < T4_PWM)
		{
			T5_PWM = T4_PWM;
		}
		fanOfficeAdvLvPwms.T1_PWM = T1_PWM;
		fanOfficeAdvLvPwms.T2_PWM = T2_PWM;
		fanOfficeAdvLvPwms.T3_PWM = T3_PWM;
		fanOfficeAdvLvPwms.T4_PWM = T4_PWM;
		fanOfficeAdvLvPwms.T5_PWM = T5_PWM;
		return fanOfficeAdvLvPwms;
	}

	private void InitalizeParameters()
	{
		if (cDefaultProfile1.F == 3 && (cDefaultProfile1.P < 3 || cDefaultProfile1.G < 3))
		{
			cDefaultProfile1.F = 2u;
		}
		if (cDefaultProfile2.F == 3 && (cDefaultProfile2.P < 3 || cDefaultProfile2.G < 3))
		{
			cDefaultProfile2.F = 2u;
		}
		if (cDefaultProfile3.F == 3 && (cDefaultProfile3.P < 3 || cDefaultProfile3.G < 3))
		{
			cDefaultProfile3.F = 2u;
		}
		if (cDefaultProfile1.F_DC == 3 && (cDefaultProfile1.P_DC < 3 || cDefaultProfile1.G_DC < 3))
		{
			cDefaultProfile1.F_DC = 2u;
		}
		if (cDefaultProfile2.F_DC == 3 && (cDefaultProfile2.P_DC < 3 || cDefaultProfile2.G_DC < 3))
		{
			cDefaultProfile2.F_DC = 2u;
		}
		if (cDefaultProfile3.F_DC == 3 && (cDefaultProfile3.P_DC < 3 || cDefaultProfile3.G_DC < 3))
		{
			cDefaultProfile3.F_DC = 2u;
		}
		if (cDefaultProfile1.F != 3 && cDefaultProfile2.F != 3 && cDefaultProfile3.F != 3)
		{
			m_HiddenFanQuietMode = 1;
		}
		else
		{
			m_HiddenFanQuietMode = 0;
		}
		if (g_PowerMode == 1)
		{
			m_CurrentIndex = m_SysPowerModeIndex;
			switch (m_CurrentIndex)
			{
			case 1u:
				m_CpuMode = cDefaultProfile1.P;
				m_DGpuMode = cDefaultProfile1.G;
				g_FanMode = cDefaultProfile1.F;
				break;
			case 2u:
				m_CpuMode = cDefaultProfile2.P;
				m_DGpuMode = cDefaultProfile2.G;
				g_FanMode = cDefaultProfile2.F;
				break;
			case 3u:
				m_CpuMode = cDefaultProfile3.P;
				m_DGpuMode = cDefaultProfile3.G;
				g_FanMode = cDefaultProfile3.F;
				break;
			}
		}
		else
		{
			m_CurrentIndex = m_SysPowerModeIndex_DC;
			switch (m_CurrentIndex)
			{
			case 1u:
				m_CpuMode = cDefaultProfile1.P_DC;
				m_DGpuMode = cDefaultProfile1.G_DC;
				g_FanMode = cDefaultProfile1.F_DC;
				break;
			case 2u:
				m_CpuMode = cDefaultProfile2.P_DC;
				m_DGpuMode = cDefaultProfile2.G_DC;
				g_FanMode = cDefaultProfile2.F_DC;
				break;
			case 3u:
				m_CpuMode = cDefaultProfile3.P_DC;
				m_DGpuMode = cDefaultProfile3.G_DC;
				g_FanMode = cDefaultProfile3.F_DC;
				break;
			}
		}
		if (m_nBenchmarkModeSupport == 0)
		{
			m_BenchmarkMode = 0u;
		}
	}

	private void Init()
	{
		InitalizeParameters();
		m_FanTableManager.FanTable_Init();
		if (m_BenchmarkMode == 1)
		{
			SetSysPowerModeIndex(4u);
			SetCpuMode(4u);
			SetDGpuModeWithOverBoost(4u, 4u, 4u);
			SetFanMode(4u);
		}
		else
		{
			SetSysPowerModeIndex(m_CurrentIndex);
			SetCpuMode(m_CpuMode);
			SetDGpuModeWithOverBoost(m_CpuMode, m_DGpuMode, g_FanMode);
			SetFanMode(g_FanMode);
		}
	}

	private void SetSysPowerModeIndex(uint mode)
	{
		SetPowerLedStatus(mode);
		SetModeProfileIndex(mode);
	}

	private void SetCpuMode(uint mode)
	{
		SetPL12(mode);
		LogCtrl.Write(className + $"[SetCpuMode] {CpuModeString(mode)}");
	}

	private void SetDGpuModeWithOverBoost(uint P, uint G, uint F)
	{
		bool bOverBoostForced = false;
		bool bOverBoostByDynamicTemp = false;
		_dispatcher?.BeginInvoke((Action)delegate
		{
			SetGPUdstateByGpuMode(G);
			SetNVPState(G);
			if (G == 4)
			{
				bOverBoostForced = true;
				bOverBoostByDynamicTemp = true;
			}
			else
			{
				bOverBoostForced = false;
				if (P == 1 && G == 1 && (F == 1 || F == 2))
				{
					bOverBoostByDynamicTemp = true;
				}
				else
				{
					bOverBoostByDynamicTemp = false;
				}
			}
			SetOverBoostMode(bOverBoostForced);
			SetOverBoostByDynamicTemp(bOverBoostByDynamicTemp);
			LogCtrl.Write(className + $"[SetDGpuModeWithOverBoost] P:{P}, G:{G}, F:{F}, bOverBoostForced:{bOverBoostForced}, bOverBoostByDynamicTemp:{bOverBoostByDynamicTemp}");
		}, DispatcherPriority.Background);
	}

	private void SetFanMode(uint mode)
	{
		switch (mode)
		{
		case 1u:
			SetFanQuietModeEnable(bEnable: false);
			SetUserHiModeToFantable(bEnable: true);
			if (g_FanEnhanced == 1)
			{
				LogCtrl.Write(className + "[SetFanMode] Performance mode, Set ECRAM 0x" + ((ushort)1873).ToString("X") + " = 0x" + ECSpec.MyFanCTLByteFlag.FanBoost_Mode.ToString("X"));
				EcCtrl.Write(GetType().Name, 1873, 64);
			}
			else
			{
				LogCtrl.Write(className + "[SetFanMode] Performance mode, Set ECRAM 0x" + ((ushort)1873).ToString("X") + " = 0x" + ECSpec.MyFanCTLByteFlag.Normal_Mode.ToString("X"));
				EcCtrl.Write(GetType().Name, 1873, 0);
			}
			break;
		case 2u:
			SetFanQuietModeEnable(bEnable: false);
			SetUserHiModeToFantable(bEnable: true);
			LogCtrl.Write(className + "[SetFanMode] Standard mode, Set ECRAM 0x" + ((ushort)1873).ToString("X") + " = 0x" + ECSpec.MyFanCTLByteFlag.User_Fan_HiMode.ToString("X"));
			EcCtrl.Write(GetType().Name, 1873, 160);
			break;
		case 3u:
			SetFanQuietModeEnable(bEnable: true);
			SetUserHiModeToFantable(bEnable: true);
			LogCtrl.Write(className + "[SetFanMode] Quiet mode, Set ECRAM 0x" + ((ushort)1873).ToString("X") + " = 0x" + ECSpec.MyFanCTLByteFlag.User_Fan_HiMode.ToString("X"));
			EcCtrl.Write(GetType().Name, 1873, 160);
			break;
		case 4u:
			LogCtrl.Write(className + "[SetFanMode] Benchmark, Set ECRAM 0x" + ((ushort)1873).ToString("X") + " = 0x" + ECSpec.MyFanCTLByteFlag.FanBoost_Mode.ToString("X"));
			EcCtrl.Write(GetType().Name, 1873, 64);
			break;
		}
		Thread.Sleep(m_FanTableDelayTime);
		SetFanTableThread(mode, g_PowerMode);
	}

	private void SetPL12(uint P)
	{
		uint num = GamingMode_PL1_Default;
		uint num2 = GamingMode_PL2_Default;
		switch (P)
		{
		case 1u:
			num = GamingMode_PL1_Default;
			num2 = GamingMode_PL2_Default;
			break;
		case 2u:
			num = OfficeMode_PL1_Default;
			num2 = OfficeMode_PL2_Default;
			break;
		case 3u:
			num = BatterySaver_PL1_Default;
			num2 = BatterySaver_PL2_Default;
			break;
		case 4u:
			num = GamingMode_PL1_Default;
			num2 = GamingMode_PL2_Default;
			break;
		}
		SetPL1Value(num);
		SetPL2Value(num2);
		LogCtrl.Write(className + "[SetPL12] Set PL12 to default: " + num + "," + num2);
	}

	private bool SetNVPState(uint G)
	{
		PressG = G;
		if (PressLock)
		{
			PressLock = false;
			pressSw.Restart();
			if (LastG != G)
			{
				SetPStateFunction(G);
			}
			Task.Run(delegate
			{
				Thread.Sleep(_SateDelay);
			}).ContinueWith(delegate
			{
				pressSw.Stop();
				PressLock = true;
				if (LastG != PressG)
				{
					SetNVPState(PressG);
				}
			});
		}
		return true;
	}

	private void SetPStateFunction(uint G)
	{
		uint num = 0u;
		uint count = 0u;
		uint GPUPstate = 0u;
		LastG = G;
		switch (G)
		{
		case 1u:
		case 4u:
			GPUPstate = 0u;
			break;
		case 2u:
			GPUPstate = 3u;
			break;
		case 3u:
			GPUPstate = 5u;
			break;
		}
		try
		{
			GPUTypeClass.GetNVGpuCount(ref count);
			for (num = 0u; num < count; num++)
			{
				if (!Monitor.TryEnter(_PStateHandler, 100))
				{
					continue;
				}
				try
				{
					if (_PStateWorker)
					{
						sw.Restart();
						if (GPUTypeClass.SetNVPState(num, ref GPUPstate))
						{
							LogCtrl.Write(className + "Set GPU " + num + ", P state: " + GPUPstate);
						}
						else
						{
							LogCtrl.Write(className + "Set GPU " + num + ", P state: " + GPUPstate + " fail");
						}
						sw.Stop();
					}
				}
				finally
				{
					if (sw.ElapsedMilliseconds > 10000)
					{
						_PStateWorker = false;
					}
					Monitor.Exit(_PStateHandler);
				}
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write(className + "Set GPU " + num + ", P state: " + GPUPstate + ", exception: " + ex.Message);
		}
	}

	private void UpdatePowerPlanFromCPUPower(uint mode)
	{
		switch (mode)
		{
		case 1u:
		{
			Guid SchemeGuid = new Guid("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c");
			PowerOptionAPI.PowerSetActiveScheme(IntPtr.Zero, ref SchemeGuid);
			break;
		}
		case 2u:
		{
			Guid SchemeGuid = new Guid("381b4222-f694-41f0-9685-ff5bb260df2e");
			PowerOptionAPI.PowerSetActiveScheme(IntPtr.Zero, ref SchemeGuid);
			break;
		}
		case 3u:
		{
			Guid SchemeGuid = new Guid("a1841308-3541-4fab-bc81-f71556f20b4a");
			PowerOptionAPI.PowerSetActiveScheme(IntPtr.Zero, ref SchemeGuid);
			break;
		}
		}
	}

	private void InitPowerPlanMonitor()
	{
		registryMonitor = new RegistryMonitor("HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Power\\User\\PowerSchemes");
	}

	private void StartPowerPlanMonitor()
	{
		if (!bStartPowerPlanMonitor)
		{
			registryMonitor.RegChanged += OnPowerPlanRegChanged;
			registryMonitor.Start();
			bStartPowerPlanMonitor = true;
		}
	}

	private void StopPowerPlanMonitor()
	{
		if (bStartPowerPlanMonitor)
		{
			registryMonitor.RegChanged -= OnPowerPlanRegChanged;
			bStartPowerPlanMonitor = false;
		}
	}

	private void OnPowerPlanRegChanged(object sender, EventArgs e)
	{
		if (bFocusCPUPowerModeByUser || m_BenchmarkMode == 1)
		{
			return;
		}
		LogCtrl.Write(className + "[OnPowerPlanRegChanged] Go in");
		string text = string.Empty;
		bool flag = false;
		try
		{
			text = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "SYSTEM\\CurrentControlSet\\Control\\Power\\User\\PowerSchemes", "ActivePowerScheme", "");
		}
		catch
		{
			LogCtrl.Write(className + "[OnPowerPlanRegChanged] RegistryKeyRead Exception");
		}
		switch (text)
		{
		case "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c":
			m_SysPowerModeIndex = 1u;
			flag = true;
			break;
		case "381b4222-f694-41f0-9685-ff5bb260df2e":
			m_SysPowerModeIndex = 2u;
			flag = true;
			break;
		case "a1841308-3541-4fab-bc81-f71556f20b4a":
			m_SysPowerModeIndex = 3u;
			flag = true;
			break;
		default:
			flag = false;
			break;
		}
		if (!flag)
		{
			return;
		}
		try
		{
			Application.Current.Dispatcher.Invoke(delegate
			{
				SetRegistry("SysPowerModeIndex", m_SysPowerModeIndex);
				SetSysPowerModeIndex(m_SysPowerModeIndex);
				switch (m_SysPowerModeIndex)
				{
				case 1u:
					m_CpuMode = cDefaultProfile1.P;
					m_DGpuMode = cDefaultProfile1.G;
					g_FanMode = cDefaultProfile1.F;
					break;
				case 2u:
					m_CpuMode = cDefaultProfile2.P;
					m_DGpuMode = cDefaultProfile2.G;
					g_FanMode = cDefaultProfile2.F;
					break;
				case 3u:
					m_CpuMode = cDefaultProfile3.P;
					m_DGpuMode = cDefaultProfile3.G;
					g_FanMode = cDefaultProfile3.F;
					break;
				}
				SetCpuMode(m_CpuMode);
				SetDGpuModeWithOverBoost(m_CpuMode, m_DGpuMode, g_FanMode);
				SetFanMode(g_FanMode);
			});
		}
		catch
		{
			LogCtrl.Write(className + "[OnPowerPlanRegChanged] Exception");
		}
	}

	private int[] GetFanTablePWMDefault()
	{
		int[] array = new int[5];
		byte Data = 0;
		byte Data2 = 0;
		byte Data3 = 0;
		byte Data4 = 0;
		byte Data5 = 0;
		EcCtrl.Read(GetType().Name, 1926, ref Data);
		EcCtrl.Read(GetType().Name, 1927, ref Data2);
		EcCtrl.Read(GetType().Name, 1928, ref Data3);
		EcCtrl.Read(GetType().Name, 1929, ref Data4);
		EcCtrl.Read(GetType().Name, 1930, ref Data5);
		array[0] = (int)(Convert.ToUInt64(Data) & 0xFF);
		array[1] = (int)(Convert.ToUInt64(Data2) & 0xFF);
		array[2] = (int)(Convert.ToUInt64(Data3) & 0xFF);
		array[3] = (int)(Convert.ToUInt64(Data4) & 0xFF);
		array[4] = (int)(Convert.ToUInt64(Data5) & 0xFF);
		return array;
	}

	private int[] CheckFanTablePWMDefault(int[] nDefaultPWM)
	{
		if (nDefaultPWM[0] == 0 || nDefaultPWM[1] == 0 || nDefaultPWM[2] == 0 || nDefaultPWM[3] == 0 || nDefaultPWM[4] == 0)
		{
			nDefaultPWM[0] = 60;
			nDefaultPWM[1] = 70;
			nDefaultPWM[2] = 80;
			nDefaultPWM[3] = 90;
			nDefaultPWM[4] = 100;
		}
		return nDefaultPWM;
	}

	private int GetBitFromByte(byte data, int num)
	{
		return (data >> num) & 1;
	}

	private int GetProjectIdFromEC()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1856, ref Data);
		return (int)(Convert.ToUInt64(Data) & 0xFF);
	}

	private void SetFanBoost(uint status)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1873, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		b = ((status != 1) ? ((byte)(b & 0xBF)) : ((byte)(b | 0x40)));
		EcCtrl.Write(GetType().Name, 1873, b);
	}

	private uint GetFanMode()
	{
		uint result = 0u;
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1873, ref Data);
		byte data = (byte)Convert.ToUInt64(Data);
		int bitFromByte = GetBitFromByte(data, 4);
		int bitFromByte2 = GetBitFromByte(data, 7);
		if (bitFromByte == 0 && bitFromByte2 == 0)
		{
			result = 0u;
		}
		else if (bitFromByte == 0 && bitFromByte2 == 1)
		{
			result = 1u;
		}
		else if (bitFromByte == 1 && bitFromByte2 == 0)
		{
			result = 2u;
		}
		LogCtrl.Write(className + $"[GetFanMode] EC 0751 bit4[{bitFromByte}], bit7[{bitFromByte2}]");
		return result;
	}

	private void SetGPUdstate(uint dstate)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1931, ref Data);
		ulong num = Convert.ToUInt64(Data);
		num &= 0xF8;
		num |= dstate;
		EcCtrl.Write(GetType().Name, 1931, (byte)num);
		LogCtrl.Write(className + "[SetGPUdstate] Set D-State to: " + dstate);
	}

	private void SetGPUdstateByGpuMode(uint G)
	{
		uint num = 1u;
		switch (G)
		{
		case 1u:
		case 2u:
		case 4u:
			num = 1u;
			break;
		case 3u:
			num = 2u;
			break;
		}
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1931, ref Data);
		ulong num2 = Convert.ToUInt64(Data);
		num2 &= 0xF8;
		num2 |= num;
		EcCtrl.Write(GetType().Name, 1931, (byte)num2);
		LogCtrl.Write(className + "[SetGPUdstate] Set D-State to: " + num);
	}

	private void SetTurboMode(uint type)
	{
		byte Data = 0;
		byte b = 243;
		byte b2 = 0;
		byte b3 = 0;
		switch (type)
		{
		case 1u:
			b2 = 0;
			break;
		case 2u:
			b2 = 4;
			break;
		case 3u:
			b2 = 8;
			break;
		case 4u:
			b2 = 12;
			break;
		}
		EcCtrl.Read(GetType().Name, 1932, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.Write(className + "[SetTurboMode] Turbo mode type " + type + ", Set ECRAM 0x" + ((ushort)1932).ToString("X") + " = 0x" + b3.ToString("X2"));
		EcCtrl.Write(GetType().Name, 1932, b3);
	}

	private uint GetTurboModeLevel()
	{
		byte Data = 0;
		byte b = 12;
		byte b2 = 0;
		uint result = 2u;
		EcCtrl.Read(GetType().Name, 1932, ref Data);
		switch ((byte)(Data & b))
		{
		case 0:
			result = 1u;
			break;
		case 4:
			result = 2u;
			break;
		case 8:
			result = 3u;
			break;
		case 12:
			result = 4u;
			break;
		}
		return result;
	}

	private int GetMyFan3p5Flag()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1934, ref Data);
		if (GetBitFromByte(Data, 2) != 1)
		{
			return 0;
		}
		return 1;
	}

	private int CheckMyFan3p5Flag()
	{
		g_MyFan3p5Flag = GetMyFan3p5Flag();
		return g_MyFan3p5Flag;
	}

	private uint GetQkeyDefine()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1922, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 2) == 2)
		{
			return 1u;
		}
		return 0u;
	}

	private int GetOfficeModeFanTableType()
	{
		int num = 0;
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1922, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 4) == 4)
		{
			return 2;
		}
		return 1;
	}

	private int GetDefaultMode()
	{
		int result = 0;
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1922, ref Data);
		switch ((byte)(Convert.ToUInt64(Data) & 0x10))
		{
		case 0:
			result = 0;
			break;
		case 16:
			result = 1;
			break;
		}
		return result;
	}

	private void SetOfficeModeAdv_MinSpeed(uint level)
	{
		EcCtrl.Write(GetType().Name, 1950, (byte)Level2Pwm(level));
	}

	private void SetOfficeModeAdv_MinTemp(uint temp)
	{
		EcCtrl.Write(GetType().Name, 1951, (byte)temp);
	}

	private void SetOfficeModeAdv_ExtraSpeed(uint level)
	{
		EcCtrl.Write(GetType().Name, 1952, (byte)level);
	}

	private void SetPowerLedStatus(uint mode)
	{
		byte Data = 0;
		byte b = 252;
		byte b2 = 0;
		byte b3 = 0;
		switch (mode)
		{
		case 2u:
			b2 = 0;
			break;
		case 1u:
			b2 = 1;
			break;
		case 3u:
			b2 = 2;
			break;
		case 4u:
			b2 = 1;
			break;
		}
		EcCtrl.Read(GetType().Name, 1957, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.Write(className + "[SetPowerLedStatus] Mode: " + mode + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"));
		EcCtrl.Write(GetType().Name, 1957, b3);
	}

	private void SetFanQuietModeEnable(bool bEnable)
	{
		byte Data = 0;
		byte b = 251;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)(bEnable ? 4 : 0);
		EcCtrl.Read(GetType().Name, 1957, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.Write(className + "[SetFanQuietModeEnable] bEnable " + bEnable + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"));
		EcCtrl.Write(GetType().Name, 1957, b3);
	}

	private void SetUserHiModeToFantable(bool bEnable)
	{
		byte Data = 0;
		byte b = 247;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)(bEnable ? 8 : 0);
		EcCtrl.Read(GetType().Name, 1957, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.Write(className + "[SetUserHiModeToFantable] bEnable " + bEnable + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"));
		EcCtrl.Write(GetType().Name, 1957, b3);
	}

	private void SetOverBoostMode(bool bEnable)
	{
		byte Data = 0;
		byte b = 239;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)(bEnable ? 16 : 0);
		EcCtrl.Read(GetType().Name, 1957, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.Write(className + "[SetOverBoostMode] bEnable " + bEnable + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"));
		EcCtrl.Write(GetType().Name, 1957, b3);
	}

	private void SetPowerStatus(bool bHigh)
	{
		byte Data = 0;
		byte b = 127;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)(bHigh ? 128 : 0);
		EcCtrl.Read(GetType().Name, 1957, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.Write(className + "[SetPowerStatus] bHigh " + bHigh + ", Set ECRAM 0x" + ((ushort)1957).ToString("X") + " = 0x" + b3.ToString("X2"));
		EcCtrl.Write(GetType().Name, 1957, b3);
	}

	private void IsFollowBiosIndex()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1957, ref Data);
		if (GetBitFromByte(Data, 7) != 1)
		{
			return;
		}
		if (g_PowerMode == 1)
		{
			m_SysPowerModeIndex = GetModeProfileIndex();
			SetRegistry("SysPowerModeIndex", m_SysPowerModeIndex);
			m_CurrentIndex = m_SysPowerModeIndex;
			switch (m_CurrentIndex)
			{
			case 1u:
				m_CpuMode = cDefaultProfile1.P;
				m_DGpuMode = cDefaultProfile1.G;
				g_FanMode = cDefaultProfile1.F;
				break;
			case 2u:
				m_CpuMode = cDefaultProfile2.P;
				m_DGpuMode = cDefaultProfile2.G;
				g_FanMode = cDefaultProfile2.F;
				break;
			case 3u:
				m_CpuMode = cDefaultProfile3.P;
				m_DGpuMode = cDefaultProfile3.G;
				g_FanMode = cDefaultProfile3.F;
				break;
			}
		}
		else
		{
			m_SysPowerModeIndex_DC = GetModeProfileIndex();
			SetRegistry("SysPowerModeIndex_DC", m_SysPowerModeIndex_DC);
			m_CurrentIndex = m_SysPowerModeIndex_DC;
			switch (m_CurrentIndex)
			{
			case 1u:
				m_CpuMode = cDefaultProfile1.P_DC;
				m_DGpuMode = cDefaultProfile1.G_DC;
				g_FanMode = cDefaultProfile1.F_DC;
				break;
			case 2u:
				m_CpuMode = cDefaultProfile2.P_DC;
				m_DGpuMode = cDefaultProfile2.G_DC;
				g_FanMode = cDefaultProfile2.F_DC;
				break;
			case 3u:
				m_CpuMode = cDefaultProfile3.P_DC;
				m_DGpuMode = cDefaultProfile3.G_DC;
				g_FanMode = cDefaultProfile3.F_DC;
				break;
			}
		}
	}

	private void SetOverBoostByDynamicTemp(bool bEnable)
	{
		byte Data = 0;
		byte b = 253;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)((!bEnable) ? 2 : 0);
		EcCtrl.Read(GetType().Name, 1958, ref Data);
		b3 = (byte)((Data & b) + b2);
		LogCtrl.Write(className + "[SetOverBoostByDynamicTemp] bEnable " + bEnable + ", Set ECRAM 0x" + ((ushort)1958).ToString("X") + " = 0x" + b3.ToString("X2"));
		EcCtrl.Write(GetType().Name, 1958, b3);
	}

	private bool IsOnApLoadFromEc()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1958, ref Data);
		if (GetBitFromByte(Data, 0) != 1)
		{
			return false;
		}
		return true;
	}

	private void SetApExist(bool exist)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1958, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		b = ((!exist) ? ((byte)(b & 0xFE)) : ((byte)(b | 1)));
		EcCtrl.Write(GetType().Name, 1958, b);
	}

	private void SetModeProfileIndex(uint mode)
	{
		uint num = 1u;
		switch (mode)
		{
		case 1u:
			num = 1u;
			break;
		case 2u:
			num = 2u;
			break;
		case 3u:
			num = 3u;
			break;
		case 4u:
			num = 1u;
			break;
		}
		EcCtrl.Write(GetType().Name, 1963, (byte)num);
		SetPowerStatus(bHigh: true);
	}

	private uint GetModeProfileIndex()
	{
		uint result = 1u;
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1963, ref Data);
		switch ((byte)(Convert.ToUInt64(Data) & 0xFF))
		{
		case 1:
			result = 1u;
			break;
		case 2:
			result = 2u;
			break;
		case 3:
			result = 3u;
			break;
		}
		return result;
	}

	private void UpdatePLDefault_ByCheckPortId()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 2043, ref Data);
		byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
		if (b == 208 || b == 213 || b == 214 || b == 215)
		{
			EcCtrl.Write(GetType().Name, 2043, 214);
			GamingMode_PL1_Default = 65u;
			GamingMode_PL2_Default = 100u;
			OfficeMode_PL1_Default = 45u;
			OfficeMode_PL2_Default = 65u;
			BatterySaver_PL1_Default = 35u;
			BatterySaver_PL2_Default = 60u;
			EcCtrl.Write(GetType().Name, 1840, (byte)GamingMode_PL1_Default);
			EcCtrl.Write(GetType().Name, 1841, (byte)GamingMode_PL2_Default);
			EcCtrl.Write(GetType().Name, 1844, (byte)OfficeMode_PL1_Default);
			EcCtrl.Write(GetType().Name, 1845, (byte)OfficeMode_PL2_Default);
			EcCtrl.Write(GetType().Name, 1959, (byte)BatterySaver_PL1_Default);
			EcCtrl.Write(GetType().Name, 1960, (byte)BatterySaver_PL2_Default);
		}
		else
		{
			GetGamingPLDefaultValue(ref GamingMode_PL1_Default, ref GamingMode_PL2_Default, ref GamingMode_PL4_Default);
			GetOfficePLDefaultValue(ref OfficeMode_PL1_Default, ref OfficeMode_PL2_Default, ref OfficeMode_PL4_Default);
			GetBatterySaverPLDefaultValue(ref BatterySaver_PL1_Default, ref BatterySaver_PL2_Default, ref BatterySaver_PL4_Default);
		}
	}

	private void GetGamingPLDefaultValue(ref uint PL1, ref uint PL2, ref uint PL4)
	{
		byte Data = 0;
		byte Data2 = 0;
		byte Data3 = 0;
		EcCtrl.Read(GetType().Name, 1840, ref Data);
		EcCtrl.Read(GetType().Name, 1841, ref Data2);
		EcCtrl.Read(GetType().Name, 1842, ref Data3);
		PL1 = (uint)(Convert.ToUInt64(Data) & 0xFF);
		PL2 = (uint)(Convert.ToUInt64(Data2) & 0xFF);
		PL4 = (uint)(Convert.ToUInt64(Data3) & 0xFF);
		LogCtrl.Write(className + "[GetGamingPLDefaultValue] PL1:" + PL1 + ", PL2:" + PL2 + ", PL4:" + PL4);
	}

	private void GetOfficePLDefaultValue(ref uint PL1, ref uint PL2, ref uint PL4)
	{
		byte Data = 0;
		byte Data2 = 0;
		byte Data3 = 0;
		EcCtrl.Read(GetType().Name, 1844, ref Data);
		EcCtrl.Read(GetType().Name, 1845, ref Data2);
		EcCtrl.Read(GetType().Name, 1846, ref Data3);
		PL1 = (uint)(Convert.ToUInt64(Data) & 0xFF);
		PL2 = (uint)(Convert.ToUInt64(Data2) & 0xFF);
		PL4 = (uint)(Convert.ToUInt64(Data3) & 0xFF);
		LogCtrl.Write(className + "[GetOfficePLDefaultValue] PL1:" + PL1 + ", PL2:" + PL2 + ", PL4:" + PL4);
	}

	private void GetBatterySaverPLDefaultValue(ref uint PL1, ref uint PL2, ref uint PL4)
	{
		byte Data = 0;
		byte Data2 = 0;
		byte Data3 = 0;
		EcCtrl.Read(GetType().Name, 1959, ref Data);
		EcCtrl.Read(GetType().Name, 1960, ref Data2);
		EcCtrl.Read(GetType().Name, 1961, ref Data3);
		PL1 = (uint)(Convert.ToUInt64(Data) & 0xFF);
		PL2 = (uint)(Convert.ToUInt64(Data2) & 0xFF);
		PL4 = (uint)(Convert.ToUInt64(Data3) & 0xFF);
		LogCtrl.Write(className + "[GetBatterySaverPLDefaultValue] PL1:" + PL1 + ", PL2:" + PL2 + ", PL4:" + PL4);
	}

	private uint GetTauDefaultValue()
	{
		uint num = 0u;
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1848, ref Data);
		num = (uint)(Convert.ToUInt64(Data) & 0xFF);
		if (num == 0)
		{
			num = 56u;
		}
		return num;
	}

	private void SetBasicFanLevel(uint level)
	{
		EcCtrl.Write(GetType().Name, 1873, (byte)(128 + level));
	}

	private void SetFan_L1_PWM(uint level)
	{
		EcCtrl.Write(GetType().Name, 1859, (byte)PWM2Byte(level));
	}

	private void SetFan_L2_PWM(uint level)
	{
		EcCtrl.Write(GetType().Name, 1860, (byte)PWM2Byte(level));
	}

	private void SetFan_L3_PWM(uint level)
	{
		EcCtrl.Write(GetType().Name, 1861, (byte)PWM2Byte(level));
	}

	private void SetFan_L4_PWM(uint level)
	{
		EcCtrl.Write(GetType().Name, 1862, (byte)PWM2Byte(level));
	}

	private void SetFan_L5_PWM(uint level)
	{
		EcCtrl.Write(GetType().Name, 1863, (byte)PWM2Byte(level));
	}

	private void SetFan_Optimized_PWM(byte pwm1, byte pwm2, byte pwm3, byte pwm4, byte pwm5)
	{
		if (pwm1 < DefaultPWM[0])
		{
			pwm1 = (byte)DefaultPWM[0];
		}
		if (pwm2 < DefaultPWM[0] || pwm2 > DefaultPWM[4])
		{
			pwm2 = (byte)DefaultPWM[1];
		}
		if (pwm3 < DefaultPWM[0] || pwm3 > DefaultPWM[4])
		{
			pwm3 = (byte)DefaultPWM[2];
		}
		if (pwm4 < DefaultPWM[0] || pwm4 > DefaultPWM[4])
		{
			pwm4 = (byte)DefaultPWM[3];
		}
		if (pwm5 > DefaultPWM[4])
		{
			pwm5 = (byte)DefaultPWM[4];
		}
		EcCtrl.Write(GetType().Name, 1859, pwm1);
		EcCtrl.Write(GetType().Name, 1860, pwm2);
		EcCtrl.Write(GetType().Name, 1861, pwm3);
		EcCtrl.Write(GetType().Name, 1862, pwm4);
		EcCtrl.Write(GetType().Name, 1863, pwm5);
	}

	private void SetFan_Optimized_PWM(FanOfficeAdvLvPwms Pwms)
	{
		EcCtrl.Write(GetType().Name, 1859, (byte)(Pwms.T1_PWM * 2));
		EcCtrl.Write(GetType().Name, 1860, (byte)(Pwms.T2_PWM * 2));
		EcCtrl.Write(GetType().Name, 1861, (byte)(Pwms.T3_PWM * 2));
		EcCtrl.Write(GetType().Name, 1862, (byte)(Pwms.T4_PWM * 2));
		EcCtrl.Write(GetType().Name, 1863, (byte)(Pwms.T5_PWM * 2));
	}

	private void SetPL1Value(ulong PL1)
	{
		EcCtrl.Write(GetType().Name, 1923, (byte)PL1);
	}

	private void SetPL2Value(ulong PL2)
	{
		EcCtrl.Write(GetType().Name, 1924, (byte)PL2);
	}

	private void SetPL4Value(ulong PL4)
	{
		EcCtrl.Write(GetType().Name, 1925, (byte)PL4);
	}

	private ulong PWM2Byte(uint level)
	{
		ulong result = 0uL;
		switch (level)
		{
		case 0u:
			result = 0uL;
			break;
		case 1u:
			result = (ulong)DefaultPWM[0];
			break;
		case 2u:
			result = (ulong)DefaultPWM[1];
			break;
		case 3u:
			result = (ulong)DefaultPWM[2];
			break;
		case 4u:
			result = (ulong)DefaultPWM[3];
			break;
		case 5u:
			result = (ulong)DefaultPWM[4];
			break;
		}
		return result;
	}

	private ulong Level2Pwm(uint level)
	{
		ulong result = 0uL;
		switch (level)
		{
		case 0u:
			result = 0uL;
			break;
		case 1u:
			result = 60uL;
			break;
		case 2u:
			result = 80uL;
			break;
		case 3u:
			result = 100uL;
			break;
		case 4u:
			result = 120uL;
			break;
		case 5u:
			result = 140uL;
			break;
		}
		return result;
	}

	private void SetFanAutoSaveRegistry(int AutoSave)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, "FanModeAutoSave", AutoSave, RegistryValueKind.DWord);
	}

	private void SetRegistry(string name, uint value, int autosave = 1)
	{
		if (autosave == 1)
		{
			switch (name)
			{
			case "SysPowerModeIndex":
			case "SysPowerModeIndex_DC":
			case "BenchmarkMode":
			case "FanEnhanced":
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath, name, value, RegistryValueKind.DWord);
				break;
			}
		}
	}

	private void SetUserProfileRegistry(string index, string name, uint value, int autosave = 1)
	{
		if (autosave == 1)
		{
			switch (name)
			{
			case "P":
			case "G":
			case "F":
			case "P_DC":
			case "G_DC":
			case "F_DC":
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_RegistryPath + "\\" + index, name, value, RegistryValueKind.DWord);
				break;
			}
		}
	}

	private void SetTauValue(uint value)
	{
	}

	private void IsSupportMyFan3()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1922, ref Data);
		if ((byte)(Convert.ToUInt64(Data) & 8) == 8)
		{
			g_SupportMyFan3 = 1;
		}
		else
		{
			g_SupportMyFan3 = 0;
		}
		LogCtrl.Write(className + "[IsSupportMyFan3] g_SupportMyFan3 = " + g_SupportMyFan3);
	}

	private string FanModeString(uint mode)
	{
		return mode switch
		{
			1u => "Performance mode", 
			2u => "Standard mode", 
			3u => "Quiet mode", 
			_ => "", 
		};
	}

	private string CpuModeString(uint mode)
	{
		return mode switch
		{
			1u => "P1", 
			2u => "P2", 
			3u => "P3", 
			4u => "Benchmark mode", 
			_ => "", 
		};
	}

	private string DGpuModeString(uint mode)
	{
		return mode switch
		{
			1u => "G1", 
			2u => "G2", 
			3u => "G3", 
			_ => "", 
		};
	}

	private async void SetNVPStateThread(uint G)
	{
		if (FansemporeSlim.CurrentCount == 0)
		{
			LastCommand = G;
			return;
		}
		await FansemporeSlim.WaitAsync();
		try
		{
			stopwatch.Reset();
			stopwatch.Start();
			new Thread((ThreadStart)delegate
			{
				SetNVPState(G);
			}).Start();
			stopwatch.Stop();
			_ = stopwatch.ElapsedMilliseconds;
		}
		catch
		{
		}
		finally
		{
			FansemporeSlim.Release();
			if (LastCommand != 0)
			{
				new Thread((ThreadStart)delegate
				{
					SetNVPState(G);
				}).Start();
				LastCommand = 0u;
			}
		}
	}

	private async void SetFanTableThread(uint _fanMode, int _powerMode)
	{
		if (FansemporeSlim2.CurrentCount == 0)
		{
			LastCommand2 = _fanMode;
			return;
		}
		await FansemporeSlim2.WaitAsync();
		try
		{
			stopwatch2.Reset();
			stopwatch2.Start();
			new Thread((ThreadStart)delegate
			{
				m_FanTableManager.SetFanTable(_fanMode, _powerMode);
			}).Start();
			stopwatch2.Stop();
			_ = stopwatch2.ElapsedMilliseconds;
		}
		catch
		{
		}
		finally
		{
			FansemporeSlim2.Release();
			if (LastCommand2 != 0)
			{
				new Thread((ThreadStart)delegate
				{
					m_FanTableManager.SetFanTable(_fanMode, _powerMode);
				}).Start();
				LastCommand2 = 0u;
			}
		}
	}
}
