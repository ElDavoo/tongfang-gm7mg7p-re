using System;
using System.Linq;
using MyControlCenter;

namespace Workaround;

public static class WKD_CriticalBatterySetting
{
	private static uint CriticalBatteryThreashold = 5u;

	public static void HardCodeLevel()
	{
		try
		{
			PowerOptionAPI.GetAll().ToList().ForEach(delegate(Guid planGuid)
			{
				PowerOptionAPI.ReadFriendlyName(planGuid);
				uint AcValueIndex = 0u;
				PowerOptionAPI.PowerReadACValueIndex(IntPtr.Zero, ref planGuid, ref PowerOptionAPI.GUID_BATTERY_SUBGROUP, ref PowerOptionAPI.GUID_CRITICAL_BATTERY_LEVEL_SETTING, ref AcValueIndex);
				if (AcValueIndex < CriticalBatteryThreashold && PowerOptionAPI.PowerWriteACValueIndex(IntPtr.Zero, ref planGuid, ref PowerOptionAPI.GUID_BATTERY_SUBGROUP, ref PowerOptionAPI.GUID_CRITICAL_BATTERY_LEVEL_SETTING, CriticalBatteryThreashold) != 0)
				{
					Console.WriteLine("PowerWriteACValueIndex fail ");
				}
				uint DcValueIndex = 0u;
				PowerOptionAPI.PowerReadDCValueIndex(IntPtr.Zero, ref planGuid, ref PowerOptionAPI.GUID_BATTERY_SUBGROUP, ref PowerOptionAPI.GUID_CRITICAL_BATTERY_LEVEL_SETTING, ref DcValueIndex);
				if (DcValueIndex < CriticalBatteryThreashold && PowerOptionAPI.PowerWriteDCValueIndex(IntPtr.Zero, ref planGuid, ref PowerOptionAPI.GUID_BATTERY_SUBGROUP, ref PowerOptionAPI.GUID_CRITICAL_BATTERY_LEVEL_SETTING, CriticalBatteryThreashold) != 0)
				{
					Console.WriteLine("PowerWriteDCValueIndex fail ");
				}
			});
		}
		catch (Exception ex)
		{
			Console.WriteLine("SetCriticalBatteryLevel error : " + ex);
		}
	}
}
