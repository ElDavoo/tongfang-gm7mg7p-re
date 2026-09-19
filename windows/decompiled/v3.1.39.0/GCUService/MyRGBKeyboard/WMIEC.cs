using System;
using System.Management;
using Utility;

namespace MyRGBKeyboard;

public static class WMIEC
{
	public delegate void ScanCode_EventHander(int scancode);

	public delegate void LM_ScanCode_EventHander(int scancode);

	private class Destructor
	{
		~Destructor()
		{
			EndWMIRecieveEvent();
		}
	}

	public const ushort OSD_KB_LED_LEVEL0 = 59;

	public const ushort OSD_KB_LED_LEVEL1 = 60;

	public const ushort OSD_KB_LED_LEVEL2 = 61;

	public const ushort OSD_KB_LED_LEVEL3 = 62;

	public const ushort OSD_KB_LED_LEVEL4 = 63;

	public static ScanCode_EventHander ScanCodeEvent;

	public static LM_ScanCode_EventHander LMScanCodeEvent;

	private static ManagementEventWatcher watcher;

	private static readonly Destructor finalObj;

	private static void WMIHandleEvent(object sender, EventArrivedEventArgs e)
	{
		try
		{
			int scancode = Convert.ToInt32(e.NewEvent.SystemProperties["ULong"].Value.ToString());
			ScanCodeEvent?.Invoke(scancode);
			LMScanCodeEvent?.Invoke(scancode);
		}
		catch
		{
		}
	}

	private static void StartWMIReceiveEvent(EventArrivedEventHandler WMIHandleEvent)
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
			Log.s(LOG_LEVEL.ERROR, string.Format("WMIEC|StartWMIReceiveEvent : An error occurred while trying to receive an event: " + ex.Message));
		}
	}

	private static void EndWMIRecieveEvent()
	{
		if (watcher != null)
		{
			watcher.Stop();
			watcher = null;
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
			Log.s(LOG_LEVEL.ERROR, string.Format("WMIEC|WMIReadECRAM : Failed" + ex.Message));
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
			Log.s(LOG_LEVEL.ERROR, string.Format("WMIEC|WMIWriteECRAM : Failed" + ex.Message));
		}
	}

	public static bool WMIWriteBiosRom(ulong Value, int KeyboardType = 0)
	{
		if (KeyboardType == 11)
		{
			try
			{
				ManagementObject managementObject = new ManagementObject("root\\WMI", "AcpiODM_Demo.InstanceName='ACPI\\PNP0C14\\2_0'", null);
				ManagementBaseObject methodParameters = managementObject.GetMethodParameters("GetUlongEx6");
				methodParameters["Data"] = Value;
				managementObject.InvokeMethod("GetUlongEx6", methodParameters, null);
				Log.s(LOG_LEVEL.TRACE, $"WMIEC|WMIWriteBiosRom GetUlongEx6: OK");
			}
			catch (ManagementException ex)
			{
				Log.s(LOG_LEVEL.ERROR, string.Format("WMIEC|WMIWriteBiosRom GetUlongEx6: Failed" + ex.Message));
				return false;
			}
		}
		else
		{
			try
			{
				ManagementObject managementObject2 = new ManagementObject("root\\WMI", "AcpiODM_Demo.InstanceName='ACPI\\PNP0C14\\2_0'", null);
				ManagementBaseObject methodParameters2 = managementObject2.GetMethodParameters("GetUlongEx7");
				methodParameters2["Data"] = Value;
				managementObject2.InvokeMethod("GetUlongEx7", methodParameters2, null);
				Log.s(LOG_LEVEL.TRACE, $"WMIEC|WMIWriteBiosRom GetUlongEx7: OK");
			}
			catch (ManagementException ex2)
			{
				Log.s(LOG_LEVEL.ERROR, string.Format("WMIEC|WMIWriteBiosRom GetUlongEx7: Failed" + ex2.Message));
				return false;
			}
		}
		return true;
	}

	static WMIEC()
	{
		watcher = null;
		finalObj = new Destructor();
		StartWMIReceiveEvent(WMIHandleEvent);
	}
}
