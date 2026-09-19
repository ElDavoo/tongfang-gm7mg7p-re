using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;

namespace MyControlCenter;

internal class PowerOptionAPI
{
	public enum AccessFlags : uint
	{
		ACCESS_SCHEME = 16u,
		ACCESS_SUBGROUP,
		ACCESS_INDIVIDUAL_SETTING
	}

	public enum NvControlPanel : byte
	{
		NV_CTRL_AUTOSELECT,
		NV_CTRL_HIGHPERFORMANE
	}

	public static Guid GUID_BATTERY_SUBGROUP = new Guid("e73a048d-bf27-4f12-9731-8b2076e8891f");

	public static Guid GUID_CRITICAL_BATTERY_LEVEL_SETTING = new Guid("9a66d8d7-4ff7-4ef9-b5a2-5a326ca2a469");

	[DllImport("powrprof.dll", SetLastError = true)]
	public static extern uint PowerReadACValue(IntPtr RootPowerKey, ref Guid SchemeGuid, ref Guid SubGroupOfPowerSettingGuid, ref Guid PowerSettingGuid, IntPtr Type, IntPtr Buffer, ref uint BufferSize);

	[DllImport("powrprof.dll", SetLastError = true)]
	public static extern uint PowerWriteACValueIndex(IntPtr RootPowerKey, ref Guid SchemeGuid, ref Guid SubGroupOfPowerSettingGuid, ref Guid PowerSettingGuid, uint AcValueIndex);

	[DllImport("powrprof.dll", SetLastError = true)]
	public static extern uint PowerReadDCValue(IntPtr RootPowerKey, ref Guid SchemeGuid, ref Guid SubGroupOfPowerSettingGuid, ref Guid PowerSettingGuid, IntPtr Type, IntPtr Buffer, ref uint BufferSize);

	[DllImport("powrprof.dll", SetLastError = true)]
	public static extern int PowerReadACValueIndex(IntPtr RootPowerKey, ref Guid SchemeGuid, ref Guid SubGroupOfPowerSettingsGuid, ref Guid PowerSettingGuid, ref uint AcValueIndex);

	[DllImport("powrprof.dll", SetLastError = true)]
	public static extern int PowerReadDCValueIndex(IntPtr RootPowerKey, ref Guid SchemeGuid, ref Guid SubGroupOfPowerSettingsGuid, ref Guid PowerSettingGuid, ref uint DcValueIndex);

	[DllImport("powrprof.dll", SetLastError = true)]
	public static extern uint PowerWriteDCValueIndex(IntPtr RootPowerKey, ref Guid SchemeGuid, ref Guid SubGroupOfPowerSettingGuid, ref Guid PowerSettingGuid, uint DcValueIndex);

	[DllImport("PowrProf.dll")]
	public static extern uint PowerEnumerate(IntPtr RootPowerKey, IntPtr SchemeGuid, IntPtr SubGroupOfPowerSettingGuid, uint AcessFlags, uint Index, ref Guid Buffer, ref uint BufferSize);

	[DllImport("PowrProf.dll")]
	public static extern uint PowerReadFriendlyName(IntPtr RootPowerKey, ref Guid SchemeGuid, IntPtr SubGroupOfPowerSettingGuid, IntPtr PowerSettingGuid, IntPtr Buffer, ref uint BufferSize);

	[DllImport("powrprof.dll", SetLastError = true)]
	public static extern uint PowerDuplicateScheme(IntPtr RootPowerKey, ref Guid SrcSchemeGuid, ref IntPtr DstSchemeGuid);

	[DllImport("powrprof.dll", CharSet = CharSet.Unicode, SetLastError = true)]
	public static extern uint PowerWriteFriendlyName(IntPtr RootPowerKey, ref Guid SchemeGuid, IntPtr SubGroupOfPowerSettingGuid, IntPtr PowerSettingGuid, string Buffer, uint BufferSize);

	[DllImport("powrprof.dll")]
	public static extern uint PowerGetActiveScheme(IntPtr UserRootPowerKey, ref IntPtr ActivePolicyGuid);

	[DllImport("powrprof.dll")]
	public static extern uint PowerDeleteScheme(IntPtr RootPowerKey, ref Guid SchemeGuid);

	[DllImport("powrprof.dll")]
	public static extern uint PowerImportPowerScheme(IntPtr RootPowerKey, string ImportFileNamePath, ref IntPtr DestinationSchemeGuid);

	[DllImport("powrprof.dll", SetLastError = true)]
	public static extern bool PowerSetActiveScheme(IntPtr RootPowerKey, ref Guid SchemeGuid);

	[DllImport("powrprof.dll")]
	public static extern bool PowerRestoreDefaultPowerSchemes();

	[DllImport("NVControlSetting.dll")]
	public static extern void SetNVCtrlPanel(byte Status);

	[DllImport("kernel32.dll")]
	private static extern IntPtr LocalFree([In] IntPtr hMem);

	public static uint DeleteScheme(Guid schemeGuid)
	{
		return PowerDeleteScheme(IntPtr.Zero, ref schemeGuid);
	}

	public static Guid powerGetActiveSchemeGuid()
	{
		IntPtr ActivePolicyGuid = IntPtr.Zero;
		uint num = PowerGetActiveScheme(IntPtr.Zero, ref ActivePolicyGuid);
		if (num == 0)
		{
			Guid result = Marshal.PtrToStructure<Guid>(ActivePolicyGuid);
			LocalFree(ActivePolicyGuid);
			return result;
		}
		throw new Exception("Error reading current power scheme. Native Win32 error code = " + num);
	}

	public static string ReadFriendlyName(Guid schemeGuid)
	{
		uint BufferSize = 1024u;
		IntPtr intPtr = Marshal.AllocHGlobal((int)BufferSize);
		try
		{
			PowerReadFriendlyName(IntPtr.Zero, ref schemeGuid, IntPtr.Zero, IntPtr.Zero, intPtr, ref BufferSize);
			return Marshal.PtrToStringUni(intPtr);
		}
		finally
		{
			Marshal.FreeHGlobal(intPtr);
		}
	}

	public static IEnumerable<Guid> GetAll()
	{
		Guid schemeGuid = Guid.Empty;
		uint sizeSchemeGuid = (uint)Marshal.SizeOf(typeof(Guid));
		for (uint schemeIndex = 0u; PowerEnumerate(IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, 16u, schemeIndex, ref schemeGuid, ref sizeSchemeGuid) == 0; schemeIndex++)
		{
			yield return schemeGuid;
		}
	}

	public static Guid powerWriteHiPerformanceName(Guid powerPlanId, string name)
	{
		Guid SchemeGuid = default(Guid);
		IntPtr DstSchemeGuid = IntPtr.Zero;
		Guid SrcSchemeGuid = new Guid("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c");
		PowerDuplicateScheme(IntPtr.Zero, ref SrcSchemeGuid, ref DstSchemeGuid);
		if (DstSchemeGuid != IntPtr.Zero)
		{
			SchemeGuid = (Guid)Marshal.PtrToStructure(DstSchemeGuid, typeof(Guid));
		}
		uint byteCount = (uint)Encoding.Unicode.GetByteCount(name);
		PowerWriteFriendlyName(IntPtr.Zero, ref SchemeGuid, IntPtr.Zero, IntPtr.Zero, name, byteCount);
		return SchemeGuid;
	}

	public static Guid powerWriteGamingModeName(string name)
	{
		Guid SchemeGuid = default(Guid);
		IntPtr DstSchemeGuid = IntPtr.Zero;
		Guid SrcSchemeGuid = new Guid("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c");
		PowerDuplicateScheme(IntPtr.Zero, ref SrcSchemeGuid, ref DstSchemeGuid);
		if (DstSchemeGuid != IntPtr.Zero)
		{
			SchemeGuid = (Guid)Marshal.PtrToStructure(DstSchemeGuid, typeof(Guid));
		}
		uint byteCount = (uint)Encoding.Unicode.GetByteCount(name);
		PowerWriteFriendlyName(IntPtr.Zero, ref SchemeGuid, IntPtr.Zero, IntPtr.Zero, name, byteCount);
		return SchemeGuid;
	}

	public static Guid powerWriteBalancedName(Guid powerPlanId, string name)
	{
		Guid SchemeGuid = default(Guid);
		IntPtr DstSchemeGuid = IntPtr.Zero;
		Guid SrcSchemeGuid = new Guid("381b4222-f694-41f0-9685-ff5bb260df2e");
		PowerDuplicateScheme(IntPtr.Zero, ref SrcSchemeGuid, ref DstSchemeGuid);
		if (DstSchemeGuid != IntPtr.Zero)
		{
			SchemeGuid = (Guid)Marshal.PtrToStructure(DstSchemeGuid, typeof(Guid));
		}
		uint byteCount = (uint)Encoding.Unicode.GetByteCount(name);
		PowerWriteFriendlyName(IntPtr.Zero, ref SchemeGuid, IntPtr.Zero, IntPtr.Zero, name, byteCount);
		return SchemeGuid;
	}

	public static Guid powerWritePowerSavingName(Guid powerPlanId, string name)
	{
		Guid SchemeGuid = default(Guid);
		IntPtr DstSchemeGuid = IntPtr.Zero;
		Guid SrcSchemeGuid = new Guid("a1841308-3541-4fab-bc81-f71556f20b4a");
		PowerDuplicateScheme(IntPtr.Zero, ref SrcSchemeGuid, ref DstSchemeGuid);
		if (DstSchemeGuid != IntPtr.Zero)
		{
			SchemeGuid = (Guid)Marshal.PtrToStructure(DstSchemeGuid, typeof(Guid));
		}
		uint byteCount = (uint)Encoding.Unicode.GetByteCount(name);
		PowerWriteFriendlyName(IntPtr.Zero, ref SchemeGuid, IntPtr.Zero, IntPtr.Zero, name, byteCount);
		return SchemeGuid;
	}

	public static int ProcessorGetValue()
	{
		Guid SchemeGuid = new Guid("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c");
		Guid SubGroupOfPowerSettingGuid = new Guid("54533251-82be-4824-96c1-47b60b740d00");
		Guid PowerSettingGuid = new Guid("893dee8e-2bef-41e0-89c6-b55d0929964c");
		new Guid("bc5038f7-23e0-4960-96da-33abaf5935ec");
		_ = IntPtr.Zero;
		uint BufferSize = 0u;
		uint num = PowerReadACValue(IntPtr.Zero, ref SchemeGuid, ref SubGroupOfPowerSettingGuid, ref PowerSettingGuid, IntPtr.Zero, IntPtr.Zero, ref BufferSize);
		if (num == 0)
		{
			IntPtr intPtr = IntPtr.Zero;
			try
			{
				intPtr = Marshal.AllocHGlobal((int)BufferSize);
				num = PowerReadACValue(IntPtr.Zero, ref SchemeGuid, ref SubGroupOfPowerSettingGuid, ref PowerSettingGuid, IntPtr.Zero, intPtr, ref BufferSize);
				byte[] array = new byte[BufferSize];
				Marshal.Copy(intPtr, array, 0, (int)BufferSize);
				return BitConverter.ToInt32(array, 0);
			}
			finally
			{
				if (intPtr != IntPtr.Zero)
				{
					Marshal.FreeHGlobal(intPtr);
				}
			}
		}
		throw new Win32Exception((int)num, "Error reading Processor value.");
	}

	public static void ProcessorSetValue(uint Value)
	{
		Guid SchemeGuid = new Guid("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c");
		Guid SubGroupOfPowerSettingGuid = new Guid("54533251-82be-4824-96c1-47b60b740d00");
		Guid PowerSettingGuid = new Guid("893dee8e-2bef-41e0-89c6-b55d0929964c");
		new Guid("bc5038f7-23e0-4960-96da-33abaf5935ec");
		PowerWriteACValueIndex(IntPtr.Zero, ref SchemeGuid, ref SubGroupOfPowerSettingGuid, ref PowerSettingGuid, Value);
	}

	public static void ACBrightnessSetValue(Guid Root, uint Value)
	{
		Guid SubGroupOfPowerSettingGuid = new Guid("7516b95f-f776-4464-8c53-06167f40cc99");
		Guid PowerSettingGuid = new Guid("aded5e82-b909-4619-9949-f5d71dac0bcb");
		PowerWriteACValueIndex(IntPtr.Zero, ref Root, ref SubGroupOfPowerSettingGuid, ref PowerSettingGuid, Value);
	}

	public static void DCBrightnessSetValue(Guid Root, uint Value)
	{
		Guid SubGroupOfPowerSettingGuid = new Guid("7516b95f-f776-4464-8c53-06167f40cc99");
		Guid PowerSettingGuid = new Guid("aded5e82-b909-4619-9949-f5d71dac0bcb");
		PowerWriteDCValueIndex(IntPtr.Zero, ref Root, ref SubGroupOfPowerSettingGuid, ref PowerSettingGuid, Value);
	}
}
