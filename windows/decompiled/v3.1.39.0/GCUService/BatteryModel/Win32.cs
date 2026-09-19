using System;
using System.IO;
using System.Runtime.InteropServices;

namespace BatteryModel;

public class Win32
{
	[Flags]
	internal enum DEVICE_GET_CLASS_FLAGS : uint
	{
		DIGCF_DEFAULT = 1u,
		DIGCF_PRESENT = 2u,
		DIGCF_ALLCLASSES = 4u,
		DIGCF_PROFILE = 8u,
		DIGCF_DEVICEINTERFACE = 0x10u
	}

	[Flags]
	internal enum LOCAL_MEMORY_FLAGS
	{
		LMEM_FIXED = 0,
		LMEM_MOVEABLE = 2,
		LMEM_NOCOMPACT = 0x10,
		LMEM_NODISCARD = 0x20,
		LMEM_ZEROINIT = 0x40,
		LMEM_MODIFY = 0x80,
		LMEM_DISCARDABLE = 0xF00,
		LMEM_VALID_FLAGS = 0xF72,
		LMEM_INVALID_HANDLE = 0x8000,
		LHND = 0x42,
		LPTR = 0x40,
		NONZEROLHND = 2,
		NONZEROLPTR = 0
	}

	[Flags]
	internal enum FILE_ATTRIBUTES : uint
	{
		Readonly = 1u,
		Hidden = 2u,
		System = 4u,
		Directory = 0x10u,
		Archive = 0x20u,
		Device = 0x40u,
		Normal = 0x80u,
		Temporary = 0x100u,
		SparseFile = 0x200u,
		ReparsePoint = 0x400u,
		Compressed = 0x800u,
		Offline = 0x1000u,
		NotContentIndexed = 0x2000u,
		Encrypted = 0x4000u,
		Write_Through = 0x80000000u,
		Overlapped = 0x40000000u,
		NoBuffering = 0x20000000u,
		RandomAccess = 0x10000000u,
		SequentialScan = 0x8000000u,
		DeleteOnClose = 0x4000000u,
		BackupSemantics = 0x2000000u,
		PosixSemantics = 0x1000000u,
		OpenReparsePoint = 0x200000u,
		OpenNoRecall = 0x100000u,
		FirstPipeInstance = 0x80000u
	}

	internal enum BATTERY_QUERY_INFORMATION_LEVEL
	{
		BatteryInformation,
		BatteryGranularityInformation,
		BatteryTemperature,
		BatteryEstimatedTime,
		BatteryDeviceName,
		BatteryManufactureDate,
		BatteryManufactureName,
		BatteryUniqueID
	}

	[Flags]
	internal enum POWER_STATE : uint
	{
		BATTERY_POWER_ONLINE = 1u,
		BATTERY_DISCHARGING = 2u,
		BATTERY_CHARGING = 4u,
		BATTERY_CRITICAL = 8u
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	internal struct BATTERY_INFORMATION
	{
		public int Capabilities;

		public byte Technology;

		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 3)]
		public byte[] Reserved;

		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 4)]
		public byte[] Chemistry;

		public int DesignedCapacity;

		public int FullChargedCapacity;

		public int DefaultAlert1;

		public int DefaultAlert2;

		public int CriticalBias;

		public int CycleCount;
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	internal struct SP_DEVICE_INTERFACE_DETAIL_DATA
	{
		public int CbSize;

		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)]
		public string DevicePath;
	}

	internal struct SP_DEVICE_INTERFACE_DATA
	{
		public int CbSize;

		public Guid InterfaceClassGuid;

		public int Flags;

		public UIntPtr Reserved;
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	internal struct BATTERY_QUERY_INFORMATION
	{
		public uint BatteryTag;

		public BATTERY_QUERY_INFORMATION_LEVEL InformationLevel;

		public int AtRate;
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	internal struct BATTERY_STATUS
	{
		public POWER_STATE PowerState;

		public uint Capacity;

		public uint Voltage;

		public int Rate;
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	internal struct BATTERY_WAIT_STATUS
	{
		public uint BatteryTag;

		public uint Timeout;

		public POWER_STATE PowerState;

		public uint LowCapacity;

		public uint HighCapacity;
	}

	internal static readonly Guid GUID_DEVCLASS_BATTERY = new Guid(1919098452, 30884, 4560, 188, 247, 0, 170, 0, 183, 179, 42);

	internal const uint IOCTL_BATTERY_QUERY_TAG = 2703424u;

	internal const uint IOCTL_BATTERY_QUERY_INFORMATION = 2703428u;

	internal const uint IOCTL_BATTERY_QUERY_STATUS = 2703436u;

	internal const int DEVICE_INTERFACE_BUFFER_SIZE = 120;

	[DllImport("setupapi.dll", CharSet = CharSet.Auto, SetLastError = true)]
	internal static extern IntPtr SetupDiGetClassDevs(ref Guid guid, [MarshalAs(UnmanagedType.LPTStr)] string enumerator, IntPtr hwnd, DEVICE_GET_CLASS_FLAGS flags);

	[DllImport("setupapi.dll", CharSet = CharSet.Auto, SetLastError = true)]
	internal static extern bool SetupDiDestroyDeviceInfoList(IntPtr deviceInfoSet);

	[DllImport("setupapi.dll", CharSet = CharSet.Auto, SetLastError = true)]
	internal static extern bool SetupDiEnumDeviceInterfaces(IntPtr hdevInfo, IntPtr devInfo, ref Guid guid, uint memberIndex, ref SP_DEVICE_INTERFACE_DATA devInterfaceData);

	[DllImport("setupapi.dll", CharSet = CharSet.Auto, SetLastError = true)]
	internal static extern bool SetupDiGetDeviceInterfaceDetail(IntPtr hdevInfo, ref SP_DEVICE_INTERFACE_DATA deviceInterfaceData, ref SP_DEVICE_INTERFACE_DETAIL_DATA deviceInterfaceDetailData, uint deviceInterfaceDetailDataSize, out uint requiredSize, IntPtr deviceInfoData);

	[DllImport("setupapi.dll", CharSet = CharSet.Auto, SetLastError = true)]
	internal static extern bool SetupDiGetDeviceInterfaceDetail(IntPtr hdevInfo, ref SP_DEVICE_INTERFACE_DATA deviceInterfaceData, IntPtr deviceInterfaceDetailData, uint deviceInterfaceDetailDataSize, out uint requiredSize, IntPtr deviceInfoData);

	[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
	internal static extern IntPtr CreateFile(string filename, [MarshalAs(UnmanagedType.U4)] FileAccess desiredAccess, [MarshalAs(UnmanagedType.U4)] FileShare shareMode, IntPtr securityAttributes, [MarshalAs(UnmanagedType.U4)] FileMode creationDisposition, [MarshalAs(UnmanagedType.U4)] FILE_ATTRIBUTES flags, IntPtr template);

	[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
	internal static extern bool DeviceIoControl(IntPtr handle, uint controlCode, [In] IntPtr inBuffer, uint inBufferSize, [Out] IntPtr outBuffer, uint outBufferSize, out uint bytesReturned, IntPtr overlapped);

	[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
	internal static extern bool DeviceIoControl(IntPtr handle, uint controlCode, ref uint inBuffer, uint inBufferSize, ref uint outBuffer, uint outBufferSize, out uint bytesReturned, IntPtr overlapped);
}
