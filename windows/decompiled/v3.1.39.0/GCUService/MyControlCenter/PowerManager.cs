using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;

namespace MyControlCenter;

internal class PowerManager
{
	private static Guid NO_SUBGROUP_GUID = new Guid("fea3413e-7e05-4911-9a71-700331f1c294");

	private static Guid GUID_DISK_SUBGROUP = new Guid("0012ee47-9041-4b5d-9b77-535fba8b1442");

	private static Guid GUID_SYSTEM_BUTTON_SUBGROUP = new Guid("4f971e89-eebd-4455-a8de-9e59040e7347");

	private static Guid GUID_PROCESSOR_SETTINGS_SUBGROUP = new Guid("54533251-82be-4824-96c1-47b60b740d00");

	private static Guid GUID_VIDEO_SUBGROUP = new Guid("7516b95f-f776-4464-8c53-06167f40cc99");

	private static Guid GUID_BATTERY_SUBGROUP = new Guid("e73a048d-bf27-4f12-9731-8b2076e8891f");

	private static Guid GUID_SLEEP_SUBGROUP = new Guid("238C9FA8-0AAD-41ED-83F4-97BE242C8F20");

	private static Guid GUID_PCIEXPRESS_SETTINGS_SUBGROUP = new Guid("501a4d13-42af-4429-9fd1-a8218c268e20");

	private const uint ERROR_MORE_DATA = 234u;

	[DllImport("powrprof.dll")]
	private static extern uint PowerEnumerate(IntPtr RootPowerKey, IntPtr SchemeGuid, ref Guid SubGroupOfPowerSetting, uint AccessFlags, uint Index, ref Guid Buffer, ref uint BufferSize);

	[DllImport("powrprof.dll")]
	private static extern uint PowerGetActiveScheme(IntPtr UserRootPowerKey, ref IntPtr ActivePolicyGuid);

	[DllImport("powrprof.dll")]
	private static extern void PowerSetActiveScheme(IntPtr UserRootPowerKey, ref IntPtr ActivePolicyGuid);

	[DllImport("powrprof.dll")]
	private static extern uint PowerReadACValue(IntPtr RootPowerKey, IntPtr SchemeGuid, IntPtr SubGroupOfPowerSettingGuid, ref Guid PowerSettingGuid, ref int Type, ref IntPtr Buffer, ref uint BufferSize);

	[DllImport("powrprof.dll", CharSet = CharSet.Unicode)]
	private static extern uint PowerReadFriendlyName(IntPtr RootPowerKey, IntPtr SchemeGuid, IntPtr SubGroupOfPowerSettingGuid, IntPtr PowerSettingGuid, StringBuilder Buffer, ref uint BufferSize);

	[DllImport("kernel32.dll")]
	private static extern IntPtr LocalFree(IntPtr hMem);

	public static void GetCurrentPowerEnumerateVistaAPI()
	{
		IntPtr ActivePolicyGuid = IntPtr.Zero;
		try
		{
			if (PowerGetActiveScheme(IntPtr.Zero, ref ActivePolicyGuid) != 0)
			{
				throw new Win32Exception();
			}
			uint BufferSize = 0u;
			StringBuilder stringBuilder = new StringBuilder();
			_ = Guid.Empty;
			_ = Guid.Empty;
			uint num = PowerReadFriendlyName(IntPtr.Zero, ActivePolicyGuid, IntPtr.Zero, IntPtr.Zero, stringBuilder, ref BufferSize);
			if (num == 234)
			{
				stringBuilder.Capacity = (int)BufferSize;
				num = PowerReadFriendlyName(IntPtr.Zero, ActivePolicyGuid, IntPtr.Zero, IntPtr.Zero, stringBuilder, ref BufferSize);
			}
			if (num != 0)
			{
				throw new Win32Exception();
			}
			Guid Buffer = Guid.Empty;
			uint num2 = 0u;
			for (uint BufferSize2 = Convert.ToUInt32(Marshal.SizeOf(typeof(Guid))); PowerEnumerate(IntPtr.Zero, ActivePolicyGuid, ref GUID_VIDEO_SUBGROUP, 18u, num2, ref Buffer, ref BufferSize2) == 0; num2++)
			{
				uint BufferSize3 = 4u;
				IntPtr Buffer2 = IntPtr.Zero;
				int Type = 0;
				num = PowerReadACValue(IntPtr.Zero, ActivePolicyGuid, IntPtr.Zero, ref Buffer, ref Type, ref Buffer2, ref BufferSize3);
				IntPtr intPtr = Marshal.AllocHGlobal(Marshal.SizeOf(GUID_VIDEO_SUBGROUP));
				Marshal.StructureToPtr(GUID_VIDEO_SUBGROUP, intPtr, fDeleteOld: false);
				IntPtr intPtr2 = Marshal.AllocHGlobal(Marshal.SizeOf(Buffer));
				Marshal.StructureToPtr(Buffer, intPtr2, fDeleteOld: false);
				uint BufferSize4 = 200u;
				StringBuilder buffer = new StringBuilder((int)BufferSize4);
				num = PowerReadFriendlyName(IntPtr.Zero, ActivePolicyGuid, intPtr, intPtr2, buffer, ref BufferSize4);
			}
		}
		finally
		{
			if (ActivePolicyGuid != IntPtr.Zero && LocalFree(ActivePolicyGuid) != IntPtr.Zero)
			{
				throw new Win32Exception();
			}
		}
	}
}
