using System;
using System.Runtime.InteropServices;
using System.Text;

namespace UsbHidModel;

internal class HIDNativeMethods
{
	[StructLayout(LayoutKind.Sequential, Pack = 1)]
	public struct DeviceInterfaceData
	{
		public int Size;

		public Guid InterfaceClassGuid;

		public int Flags;

		public IntPtr Reserved;
	}

	[StructLayout(LayoutKind.Sequential, Pack = 1)]
	public struct DeviceInterfaceDetailData
	{
		public int Size;

		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)]
		public string DevicePath;
	}

	[StructLayout(LayoutKind.Sequential, Pack = 1)]
	public struct HidCaps
	{
		public ushort Usage;

		public ushort UsagePage;

		public ushort InputReportByteLength;

		public ushort OutputReportByteLength;

		public ushort FeatureReportByteLength;

		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 17)]
		public ushort[] Reserved;

		public ushort NumberLinkCollectionNodes;

		public ushort NumberInputButtonCaps;

		public ushort NumberInputValueCaps;

		public ushort NumberInputDataIndices;

		public ushort NumberOutputButtonCaps;

		public ushort NumberOutputValueCaps;

		public ushort NumberOutputDataIndices;

		public ushort NumberFeatureButtonCaps;

		public ushort NumberFeatureValueCaps;

		public ushort NumberFeatureDataIndices;
	}

	public struct HIDD_ATTRIBUTES
	{
		public uint Size;

		public ushort VendorID;

		public ushort ProductID;

		public ushort VersionNumber;
	}

	public struct HidP_Range
	{
		public short UsageMin;

		public short UsageMax;

		public short StringMin;

		public short StringMax;

		public short DesignatorMin;

		public short DesignatorMax;

		public short DataIndexMin;

		public short DataIndexMax;
	}

	public struct HidP_NotRange
	{
		public short Usage;

		public short Reserved1;

		public short StringIndex;

		public short Reserved2;

		public short DesignatorIndex;

		public short Reserved3;

		public short DataIndex;

		public short Reserved4;
	}

	[StructLayout(LayoutKind.Explicit)]
	public struct HidP_Button_Caps
	{
		[FieldOffset(0)]
		public short UsagePage;

		[FieldOffset(2)]
		public byte ReportID;

		[FieldOffset(3)]
		[MarshalAs(UnmanagedType.U1)]
		public bool IsAlias;

		[FieldOffset(4)]
		public short BitField;

		[FieldOffset(6)]
		public short LinkCollection;

		[FieldOffset(8)]
		public short LinkUsage;

		[FieldOffset(10)]
		public short LinkUsagePage;

		[FieldOffset(12)]
		[MarshalAs(UnmanagedType.U1)]
		public bool IsRange;

		[FieldOffset(13)]
		[MarshalAs(UnmanagedType.U1)]
		public bool IsStringRange;

		[FieldOffset(14)]
		[MarshalAs(UnmanagedType.U1)]
		public bool IsDesignatorRange;

		[FieldOffset(15)]
		[MarshalAs(UnmanagedType.U1)]
		public bool IsAbsolute;

		[FieldOffset(16)]
		[MarshalAs(UnmanagedType.ByValArray, SizeConst = 10)]
		public int[] Reserved;

		[FieldOffset(56)]
		public HidP_Range Range;

		[FieldOffset(56)]
		public HidP_NotRange NotRange;
	}

	[StructLayout(LayoutKind.Explicit)]
	public struct HidP_Value_Caps
	{
		[FieldOffset(0)]
		public short UsagePage;

		[FieldOffset(2)]
		public byte ReportID;

		[FieldOffset(3)]
		[MarshalAs(UnmanagedType.I1)]
		public bool IsAlias;

		[FieldOffset(4)]
		public short BitField;

		[FieldOffset(6)]
		public short LinkCollection;

		[FieldOffset(8)]
		public short LinkUsage;

		[FieldOffset(10)]
		public short LinkUsagePage;

		[FieldOffset(12)]
		[MarshalAs(UnmanagedType.I1)]
		public bool IsRange;

		[FieldOffset(13)]
		[MarshalAs(UnmanagedType.I1)]
		public bool IsStringRange;

		[FieldOffset(14)]
		[MarshalAs(UnmanagedType.I1)]
		public bool IsDesignatorRange;

		[FieldOffset(15)]
		[MarshalAs(UnmanagedType.I1)]
		public bool IsAbsolute;

		[FieldOffset(16)]
		[MarshalAs(UnmanagedType.I1)]
		public bool HasNull;

		[FieldOffset(17)]
		public char Reserved;

		[FieldOffset(18)]
		public short BitSize;

		[FieldOffset(20)]
		public short ReportCount;

		[FieldOffset(22)]
		public short Reserved2a;

		[FieldOffset(24)]
		public short Reserved2b;

		[FieldOffset(26)]
		public short Reserved2c;

		[FieldOffset(28)]
		public short Reserved2d;

		[FieldOffset(30)]
		public short Reserved2e;

		[FieldOffset(32)]
		public short UnitsExp;

		[FieldOffset(34)]
		public short Units;

		[FieldOffset(36)]
		public short LogicalMin;

		[FieldOffset(38)]
		public short LogicalMax;

		[FieldOffset(40)]
		public short PhysicalMin;

		[FieldOffset(42)]
		public short PhysicalMax;

		[FieldOffset(44)]
		public HidP_Range Range;

		[FieldOffset(44)]
		public HidP_NotRange NotRange;
	}

	public enum HIDP_REPORT_TYPE
	{
		HidP_Input,
		HidP_Output,
		HidP_Feature
	}

	[StructLayout(LayoutKind.Explicit)]
	public struct HIDP_DATA
	{
		[FieldOffset(0)]
		public short DataIndex;

		[FieldOffset(2)]
		public short Reserved;

		[FieldOffset(4)]
		public int RawValue;

		[FieldOffset(4)]
		[MarshalAs(UnmanagedType.U1)]
		public bool On;
	}

	public const int DIGCF_PRESENT = 2;

	public const int DIGCF_DEVICEINTERFACE = 16;

	public const int HIDP_STATUS_SUCCESS = 1114112;

	public const int HIDP_STATUS_NULL = -2146369535;

	public const int HIDP_STATUS_INVALID_PREPARSED_DATA = -1072627711;

	public const int HIDP_STATUS_INVALID_REPORT_TYPE = -1072627710;

	public const int HIDP_STATUS_INVALID_REPORT_LENGTH = -1072627709;

	public const int HIDP_STATUS_USAGE_NOT_FOUND = -1072627708;

	public const int HIDP_STATUS_VALUE_OUT_OF_RANGE = -1072627707;

	public const int HIDP_STATUS_BAD_LOG_PHY_VALUES = -1072627706;

	public const int HIDP_STATUS_BUFFER_TOO_SMALL = -1072627705;

	public const int HIDP_STATUS_INTERNAL_ERROR = -1072627704;

	public const int HIDP_STATUS_I8042_TRANS_UNKNOWN = -1072627703;

	public const int HIDP_STATUS_INCOMPATIBLE_REPORT_ID = -1072627702;

	public const int HIDP_STATUS_NOT_VALUE_ARRAY = -1072627701;

	public const int HIDP_STATUS_IS_VALUE_ARRAY = -1072627700;

	public const int HIDP_STATUS_DATA_INDEX_NOT_FOUND = -1072627699;

	public const int HIDP_STATUS_DATA_INDEX_OUT_OF_RANGE = -1072627698;

	public const int HIDP_STATUS_BUTTON_NOT_PRESSED = -1072627697;

	public const int HIDP_STATUS_REPORT_DOES_NOT_EXIST = -1072627696;

	public const int HIDP_STATUS_NOT_IMPLEMENTED = -1072627680;

	public const uint GENERIC_READ = 2147483648u;

	public const uint GENERIC_WRITE = 1073741824u;

	public const uint FILE_SHARE_WRITE = 2u;

	public const uint FILE_SHARE_READ = 1u;

	public const uint FILE_FLAG_OVERLAPPED = 1073741824u;

	public const uint OPEN_EXISTING = 3u;

	public const uint OPEN_ALWAYS = 4u;

	public static IntPtr NullHandle = IntPtr.Zero;

	public static IntPtr InvalidHandleValue = new IntPtr(-1);

	[DllImport("setupapi.dll", SetLastError = true)]
	public static extern bool SetupDiGetDeviceInterfaceDetail(IntPtr lpDeviceInfoSet, ref DeviceInterfaceData oInterfaceData, IntPtr lpDeviceInterfaceDetailData, uint nDeviceInterfaceDetailDataSize, ref uint nRequiredSize, IntPtr lpDeviceInfoData);

	[DllImport("setupapi.dll", SetLastError = true)]
	public static extern bool SetupDiGetDeviceInterfaceDetail(IntPtr lpDeviceInfoSet, ref DeviceInterfaceData oInterfaceData, ref DeviceInterfaceDetailData oDetailData, uint nDeviceInterfaceDetailDataSize, ref uint nRequiredSize, IntPtr lpDeviceInfoData);

	[DllImport("setupapi.dll", SetLastError = true)]
	public static extern bool SetupDiEnumDeviceInterfaces(IntPtr lpDeviceInfoSet, uint nDeviceInfoData, ref Guid gClass, uint nIndex, ref DeviceInterfaceData oInterfaceData);

	[DllImport("setupapi.dll", SetLastError = true)]
	public static extern bool SetupDiDestroyDeviceInfoList(IntPtr lpInfoSet);

	[DllImport("setupapi.dll", SetLastError = true)]
	public static extern IntPtr SetupDiGetClassDevs(ref Guid gClass, [MarshalAs(UnmanagedType.LPStr)] string strEnumerator, IntPtr hParent, uint nFlags);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern void HidD_GetHidGuid(out Guid gHid);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern bool HidD_GetPreparsedData(IntPtr hFile, out IntPtr lpData);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern bool HidD_FreePreparsedData(int lData);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern int HidP_GetCaps(IntPtr lpData, out HidCaps oCaps);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern bool HidD_FreePreparsedData(ref IntPtr pData);

	[DllImport("hid.dll", CharSet = CharSet.Auto, SetLastError = true)]
	public static extern bool HidD_GetManufacturerString(IntPtr hFile, StringBuilder buffer, int bufferLength);

	[DllImport("hid.dll", CharSet = CharSet.Auto, SetLastError = true)]
	public static extern bool HidD_GetProductString(IntPtr hFile, StringBuilder buffer, int bufferLength);

	[DllImport("hid.dll", CharSet = CharSet.Auto, SetLastError = true)]
	internal static extern bool HidD_GetSerialNumberString(IntPtr hDevice, StringBuilder buffer, int bufferLength);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern bool HidD_GetAttributes(IntPtr hFile, ref HIDD_ATTRIBUTES attributes);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern bool HidD_SetOutputReport(IntPtr hFile, byte[] lpReportBuffer, int reportBufferLength);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern bool HidD_GetFeature(IntPtr hFile, byte[] lpReportBuffer, int reportBufferLengths);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern bool HidD_SetFeature(IntPtr hFile, byte[] lpReportBuffer, int reportBufferLengths);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern int HidP_GetButtonCaps(HIDP_REPORT_TYPE reportType, [In][Out] HidP_Button_Caps[] buttonCaps, ref short buttonCapsLength, IntPtr preparsedData);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern int HidP_GetValueCaps(HIDP_REPORT_TYPE reportType, [In][Out] HidP_Value_Caps[] valueCaps, ref short valueCapsLength, IntPtr preparsedData);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern int HidP_InitializeReportForID(HIDP_REPORT_TYPE reportType, byte reportID, IntPtr preparsedData, [MarshalAs(UnmanagedType.LPArray, SizeParamIndex = 4)] byte[] report, int reportLength);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern int HidP_SetUsages(HIDP_REPORT_TYPE reportType, short usagePage, short linkCollection, [In][Out] HIDP_DATA[] usageList, ref int usageLength, IntPtr preparsedData, [MarshalAs(UnmanagedType.LPArray, SizeParamIndex = 4)] byte[] report, int reportLength);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern int HidP_SetData(HIDP_REPORT_TYPE reportType, [In][Out] HIDP_DATA[] dataList, ref int dataLength, IntPtr preparsedData, [MarshalAs(UnmanagedType.LPArray, SizeParamIndex = 5)] byte[] report, int reportLength);

	[DllImport("hid.dll", SetLastError = true)]
	public static extern int HidP_GetData(HIDP_REPORT_TYPE reportType, [In][Out] HIDP_DATA[] dataList, ref int dataLength, IntPtr preparsedData, [MarshalAs(UnmanagedType.LPArray, SizeParamIndex = 5)] byte[] report, int reportLength);

	[DllImport("kernel32.dll", SetLastError = true)]
	public static extern IntPtr CreateFile([MarshalAs(UnmanagedType.LPStr)] string strName, uint nAccess, uint nShareMode, IntPtr lpSecurity, uint nCreationFlags, uint nAttributes, IntPtr lpTemplate);

	[DllImport("kernel32.dll", SetLastError = true)]
	public static extern bool CloseHandle(IntPtr hObject);
}
