using System;
using System.IO;
using System.Management;
using System.Reflection;
using GCUService.MySetting.Muter;
using MyECIO;
using Utility;

namespace MyControlCenter;

public class WMIEC
{
	public delegate void ScanCode_EventHander(int scancode);

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static MyFanCtrl m_MyFan = MyFanCtrl.Instance;

	private static ScanCode_EventHander[] listener = new ScanCode_EventHander[16];

	private static ManagementEventWatcher watcher = null;

	public const int SMRW_CMD_OFFSET = 0;

	public const int SMRW_VALUE_OFFSET = 8;

	public const byte SMRW_CMD_MIN = 0;

	public const byte SMRW_CMD_READ = 187;

	public const byte SMRW_CMD_WRITE = 170;

	public const byte SMRW_CMD_MAX = byte.MaxValue;

	public const int GETSETULONG2_ADDR_OFFSET = 0;

	public const int GETSETULONG2_VALUE_OFFSET = 32;

	public const int GETSETULONG2_OFFSET_OFFSET = 40;

	public const int GETSETULONG2_CMD_OFFSET = 56;

	public const ulong GETSETULONG2_CMD_READ_SMART_APC_TABLE = 12uL;

	public const ulong GETSETULONG2_CMD_WRITE_SMART_APC_TABLE = 13uL;

	public void WMIHandleEvent(object sender, EventArrivedEventArgs e)
	{
		try
		{
			int num = Convert.ToInt32(e.NewEvent.SystemProperties["ULong"].Value.ToString());
			switch (num)
			{
			case 64:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} OSD_WINKEY_LOCK");
				App.m_MySetting.m_Manager.UpdateWinKeyStatus(1);
				App.m_MySetting.m_Manager.SetWinKeyREG(1);
				App.m_MySetting.m_Manager.UpdateStatusToClient(1);
				App.m_Osd.SetOsdWay(num);
				break;
			case 65:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} OSD_WINKEY_LOCK");
				App.m_MySetting.m_Manager.UpdateWinKeyStatus(0);
				App.m_MySetting.m_Manager.SetWinKeyREG(0);
				App.m_MySetting.m_Manager.UpdateStatusToClient(1);
				App.m_Osd.SetOsdWay(num);
				break;
			case 1:
			case 3:
			case 4:
			case 5:
				App.m_Osd?.SetOsdWay(num);
				break;
			case 2:
				App.m_Osd.SetOsdWay(num);
				App.m_MySetting.m_Manager.InitNumPad();
				App.m_MySetting.m_Manager.UpdateStatusToClient(1);
				break;
			case 59:
			case 60:
			case 61:
			case 62:
			case 63:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} OSD_KB_LED_LEVEL");
				App.m_Osd.ShowBLOSD(num);
				break;
			case 169:
				App.m_Osd.SetPanelStatus();
				break;
			case 164:
			{
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} OSD_AIRPLANEMODE");
				bool airplaneOnOff = AirplaneModeCtrl.SetAirplaneModeNoDriver();
				App.m_Osd.SetOsdWay(num, airplaneOnOff);
				break;
			}
			case 165:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} WinKey_Update");
				break;
			case 57:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X}");
				if (CustomizeInfo.m_sLightbarType != "1")
				{
					return;
				}
				LogCtrl.Write("EC ScanCode BREATH LED ON");
				MySettingParams.sLightBar_Status = "LIGHTBAR_STATUS_ON";
				App.m_MySetting.m_Manager.UpdateStatusToClient(1);
				break;
			case 58:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X}");
				if (CustomizeInfo.m_sLightbarType != "1")
				{
					return;
				}
				LogCtrl.Write("EC ScanCode BREATH LED OFF");
				MySettingParams.sLightBar_Status = "LIGHTBAR_STATUS_OFF";
				App.m_MySetting.m_Manager.UpdateStatusToClient(1);
				break;
			case 176:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} OSD_FanModeSwitch");
				m_MyFan.ModeSwitchChanged();
				break;
			case 167:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} OSD_FANBOOST_UPDATE");
				m_MyFan.FanBoostUpdate();
				break;
			case 170:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} TimAP_MyFanOT");
				break;
			case 173:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} TimAP_ReleaseUSM");
				break;
			case 172:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} TimAP_MyBat_HPOff");
				m_MyFan.FanBoostOffFromEC();
				break;
			case 187:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} TimAP_HighTemp");
				m_MyFan.SafetyProtectionUpdate();
				break;
			case 175:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} TimAP_HaierLB_Sw");
				if (CustomizeInfo.m_sLightbarType == "0" || CustomizeInfo.m_sLightbarType == "1" || CustomizeInfo.m_sLightbarType == "3")
				{
					return;
				}
				if (CustomizeInfo.m_sLightbarType == "2")
				{
					uint powerStatus = MyRgbLightbarCtrl.Instance.GetPowerStatus();
					string text2 = ((powerStatus == 1) ? "POWER_OFF" : "POWER_ON");
					LogCtrl.TraceMessage("curr_rgblb_powerstatus:" + powerStatus + " -> " + text2, "WMIHandleEvent", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\WMIEC.cs", 186);
					App.m_MQTTService.Publish("MyRgbLightbar/Control", new
					{
						Action = text2
					}, retain: false);
				}
				else
				{
					LogCtrl.TraceMessage("Unhandled light bar type", "WMIHandleEvent", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\WMIEC.cs", 193);
				}
				break;
			case 179:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} BacklightLevelChange");
				if (CustomizeInfo.m_sKeyboardType == "2")
				{
					App.m_MySetting.m_Manager.BacklightLevelChanged();
					App.m_MySetting.m_Manager.UpdateStatusToClient(1);
				}
				break;
			case 180:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} BacklightPowerChange");
				if (CustomizeInfo.m_sKeyboardType == "2")
				{
					App.m_MySetting.m_Manager.BacklightPowerChanged();
					App.m_MySetting.m_Manager.UpdateStatusToClient(1);
				}
				break;
			case 183:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} TimAP_MicMute_Sw");
				MicMuteControl.Instance.Trigger();
				break;
			case 184:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} OSD_FnChange");
				App.m_MySetting.m_Manager.UpdateFnKeyStatus();
				App.m_MySetting.m_Manager.UpdateStatusToClient(1);
				App.m_Osd.SetOsdWay(num);
				break;
			case 186:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} CallAp");
				try
				{
					string text = LogCtrl.GetParentDirectoryPath(new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName, 2) + "\\GamingCenter";
					if (text != "")
					{
						CreateProcessAsUserWrapper.LaunchChildProcess(text + "\\ControlCenterU.exe");
					}
				}
				catch (Exception ex)
				{
					LogCtrl.Write("LaunchAP Exception: " + ex.Message);
				}
				break;
			case 188:
				LogCtrl.Write("---------------" + LogCtrl.GetTime() + "---------------");
				LogCtrl.Write($"AP receive 0x{num:X} TimAP_WhisperUpdate");
				m_MyFan.WhisperUpdate();
				break;
			default:
				Console.WriteLine("{0}", num);
				break;
			}
			ScanCode_EventHander[] array = listener;
			for (int i = 0; i < array.Length; i++)
			{
				array[i]?.Invoke(num);
			}
		}
		catch (Exception ex2)
		{
			LogCtrl.TraceMessage(ex2.ToString(), "WMIHandleEvent", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\WMIEC.cs", 290);
		}
	}

	public void StartWMIReceiveEvent(EventArrivedEventHandler WMIHandleEvent)
	{
		try
		{
			WqlEventQuery query = new WqlEventQuery("SELECT * FROM AcpiTest_EventULong");
			watcher = new ManagementEventWatcher(new ManagementScope("\\\\.\\Root\\WMI"), query);
			watcher.EventArrived += WMIHandleEvent;
			watcher.Start();
		}
		catch (ManagementException ex)
		{
			Console.WriteLine("An error occurred while trying to receive an event: " + ex.Message);
		}
	}

	public void EndWMIRecieveEvent()
	{
		if (watcher != null)
		{
			watcher.Stop();
			watcher = null;
		}
		if (listener != null)
		{
			listener = null;
		}
	}

	public static bool WMIReadECRAM(ulong Addr, ref object data)
	{
		try
		{
			ManagementObject managementObject = new ManagementObject("root\\WMI", "AcpiTest_MULong.InstanceName='ACPI\\PNP0C14\\1_1'", null);
			ManagementBaseObject methodParameters = managementObject.GetMethodParameters("GetSetULong");
			Addr = 1099511627776L + Addr;
			methodParameters["Data"] = Addr;
			ManagementBaseObject managementBaseObject = managementObject.InvokeMethod("GetSetULong", methodParameters, null);
			data = managementBaseObject["Return"];
			return true;
		}
		catch (ManagementException ex)
		{
			LogCtrl.Write("WMIReadECRAM: GetSetULong failed, Addr: 0x" + Addr.ToString("X") + ", error message: " + ex.Message);
			Console.WriteLine("GetSetULong failed" + ex.Message);
			return false;
		}
	}

	public static void WMIWriteECRAM(ulong Addr, ulong Value)
	{
		try
		{
			ManagementObject managementObject = new ManagementObject("root\\WMI", "AcpiTest_MULong.InstanceName='ACPI\\PNP0C14\\1_1'", null);
			ManagementBaseObject methodParameters = managementObject.GetMethodParameters("GetSetULong");
			Value <<= 16;
			Addr = Value + Addr;
			methodParameters["Data"] = Addr;
			managementObject.InvokeMethod("GetSetULong", methodParameters, null);
		}
		catch (ManagementException ex)
		{
			LogCtrl.Write("WMIWriteECRAM: GetSetULong failed, Addr: " + Addr + ", error message: " + ex.Message);
			Console.WriteLine("GetSetULong failed" + ex.Message);
		}
	}

	public static void WMIWriteBiosRAM(ulong Value)
	{
		try
		{
			ManagementObject managementObject = new ManagementObject("root\\WMI", "AcpiODM_Demo.InstanceName='ACPI\\PNP0C14\\2_0'", null);
			ManagementBaseObject methodParameters = managementObject.GetMethodParameters("GetUlongEx7");
			methodParameters["Data"] = Value;
			managementObject.InvokeMethod("GetUlongEx7", methodParameters, null);
		}
		catch (ManagementException ex)
		{
			Console.WriteLine("WMIWriteBiosRAM : Failed" + ex.Message);
			LogCtrl.Write("WMIWriteBiosRAM : Failed" + ex.Message);
		}
	}

	public static ulong Combine(byte b7, byte b6, byte b5, byte b4, byte b3, byte b2, byte b1, byte b0)
	{
		return Convert.ToUInt64(BitConverter.ToInt64(new byte[8] { b0, b1, b2, b3, b4, b5, b6, b7 }, 0));
	}

	public static void Smrw(ulong Cmd, ulong Value, ref object RetData)
	{
		try
		{
			ManagementObject managementObject = new ManagementObject("root\\WMI", "AcpiTest_MULong.InstanceName='ACPI\\PNP0C14\\1_1'", null);
			ManagementBaseObject methodParameters = managementObject.GetMethodParameters("SMRW");
			ulong num = Cmd + (Value << 8);
			methodParameters["Data"] = num;
			Console.WriteLine("0x" + num.ToString("X"));
			ManagementBaseObject managementBaseObject = managementObject.InvokeMethod("SMRW", methodParameters, null);
			RetData = managementBaseObject["Return"];
		}
		catch (ManagementException ex)
		{
			Console.WriteLine("Smrw: failed, error        : " + ex);
			LogCtrl.TraceMessage("Smrw: failed, error        : " + ex, "Smrw", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\WMIEC.cs", 478);
		}
	}

	public static void GetSetULong2(ulong Cmd, ref object RetData)
	{
		GetSetULong2(Cmd, 0uL, 0uL, 0uL, ref RetData);
	}

	public static void GetSetULong2(ulong Cmd, ulong Addr, ulong Offset, ulong Value, ref object RetData)
	{
		try
		{
			ManagementObject managementObject = new ManagementObject("root\\WMI", "AcpiTest_MULong.InstanceName='ACPI\\PNP0C14\\1_1'", null);
			ManagementBaseObject methodParameters = managementObject.GetMethodParameters("GetSetULong2");
			ulong num;
			if (Cmd == 13)
			{
				Value &= 0xFFFFFFFFFFFFFFL;
				num = (Cmd << 56) + Value;
			}
			else
			{
				num = (Cmd << 56) + (Offset << 40) + (Value << 32) + Addr;
			}
			methodParameters["Data"] = num;
			Console.WriteLine("0x" + num.ToString("X"));
			ManagementBaseObject managementBaseObject = managementObject.InvokeMethod("GetSetULong2", methodParameters, null);
			RetData = managementBaseObject["Return"];
		}
		catch (ManagementException ex)
		{
			Console.WriteLine("GETSETULONG2: failed, error        : " + ex);
		}
	}
}
