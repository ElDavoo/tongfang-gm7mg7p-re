using System;
using System.Runtime.InteropServices;

namespace Magic.Samples.DisplaySettings;

internal static class SafeNativeMethods
{
	[Flags]
	public enum ChangeDisplaySettingsFlags : uint
	{
		CDS_NONE = 0u,
		CDS_UPDATEREGISTRY = 1u,
		CDS_TEST = 2u,
		CDS_FULLSCREEN = 4u,
		CDS_GLOBAL = 8u,
		CDS_SET_PRIMARY = 0x10u,
		CDS_VIDEOPARAMETERS = 0x20u,
		CDS_ENABLE_UNSAFE_MODES = 0x100u,
		CDS_DISABLE_UNSAFE_MODES = 0x200u,
		CDS_RESET = 0x40000000u,
		CDS_RESET_EX = 0x20000000u,
		CDS_NORESET = 0x10000000u
	}

	public struct DEVMODE
	{
		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
		public string dmDeviceName;

		[MarshalAs(UnmanagedType.U2)]
		public ushort dmSpecVersion;

		[MarshalAs(UnmanagedType.U2)]
		public ushort dmDriverVersion;

		[MarshalAs(UnmanagedType.U2)]
		public ushort dmSize;

		[MarshalAs(UnmanagedType.U2)]
		public ushort dmDriverExtra;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmFields;

		public POINTL dmPosition;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmDisplayOrientation;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmDisplayFixedOutput;

		[MarshalAs(UnmanagedType.I2)]
		public short dmColor;

		[MarshalAs(UnmanagedType.I2)]
		public short dmDuplex;

		[MarshalAs(UnmanagedType.I2)]
		public short dmYResolution;

		[MarshalAs(UnmanagedType.I2)]
		public short dmTTOption;

		[MarshalAs(UnmanagedType.I2)]
		public short dmCollate;

		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
		public string dmFormName;

		[MarshalAs(UnmanagedType.U2)]
		public ushort dmLogPixels;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmBitsPerPel;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmPelsWidth;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmPelsHeight;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmDisplayFlags;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmDisplayFrequency;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmICMMethod;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmICMIntent;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmMediaType;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmDitherType;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmReserved1;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmReserved2;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmPanningWidth;

		[MarshalAs(UnmanagedType.U4)]
		public uint dmPanningHeight;

		public void Initialize()
		{
			dmDeviceName = new string(new char[32]);
			dmFormName = new string(new char[32]);
			dmSize = (ushort)Marshal.SizeOf(this);
		}
	}

	public struct DISPLAY_DEVICE
	{
		[MarshalAs(UnmanagedType.U4)]
		public int cb;

		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
		public string DeviceName;

		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
		public string DeviceString;

		[MarshalAs(UnmanagedType.U4)]
		public DisplayDeviceStateFlags StateFlags;

		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
		public string DeviceID;

		[MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
		public string DeviceKey;
	}

	[Flags]
	public enum DisplayDeviceStateFlags
	{
		AttachedToDesktop = 1,
		MultiDriver = 2,
		PrimaryDevice = 4,
		MirroringDriver = 8,
		VGACompatible = 0x10,
		Removable = 0x20,
		ModesPruned = 0x8000000,
		Remote = 0x4000000,
		Disconnect = 0x2000000
	}

	public struct POINTL
	{
		public int x;

		public int y;
	}

	public const int ENUM_CURRENT_SETTINGS = -1;

	public const int DMDO_DEFAULT = 0;

	public const int DMDO_90 = 1;

	public const int DMDO_180 = 2;

	public const int DMDO_270 = 3;

	public const uint FORMAT_MESSAGE_FROM_HMODULE = 2048u;

	public const uint FORMAT_MESSAGE_ALLOCATE_BUFFER = 256u;

	public const uint FORMAT_MESSAGE_IGNORE_INSERTS = 512u;

	public const uint FORMAT_MESSAGE_FROM_SYSTEM = 4096u;

	public const uint FORMAT_MESSAGE_FLAGS = 4864u;

	[DllImport("user32.dll")]
	public static extern bool EnumDisplaySettings(string lpszDeviceName, int iModeNum, ref DEVMODE lpDevMode);

	[DllImport("User32.dll", BestFitMapping = false, SetLastError = true, ThrowOnUnmappableChar = true)]
	[return: MarshalAs(UnmanagedType.I4)]
	public static extern int ChangeDisplaySettings([In][Out] ref DEVMODE lpDevMode, [MarshalAs(UnmanagedType.U4)] uint dwflags);

	[DllImport("user32.dll")]
	public static extern DisplayChangeResult ChangeDisplaySettingsEx(string lpszDeviceName, ref DEVMODE lpDevMode, IntPtr hwnd, ChangeDisplaySettingsFlags dwflags, IntPtr lParam);

	[DllImport("user32.dll")]
	public static extern DisplayChangeResult ChangeDisplaySettingsEx(string lpszDeviceName, IntPtr lpDevMode, IntPtr hwnd, ChangeDisplaySettingsFlags dwflags, IntPtr lParam);

	[DllImport("kernel32.dll", BestFitMapping = false, SetLastError = true, ThrowOnUnmappableChar = true)]
	[return: MarshalAs(UnmanagedType.Bool)]
	public static extern uint FormatMessage([MarshalAs(UnmanagedType.U4)] uint dwFlags, [MarshalAs(UnmanagedType.U4)] uint lpSource, [MarshalAs(UnmanagedType.U4)] uint dwMessageId, [MarshalAs(UnmanagedType.U4)] uint dwLanguageId, [MarshalAs(UnmanagedType.LPTStr)] out string lpBuffer, [MarshalAs(UnmanagedType.U4)] uint nSize, [MarshalAs(UnmanagedType.U4)] uint Arguments);

	[DllImport("User32.dll")]
	public static extern bool EnumDisplayDevices(string lpDevice, uint iDevNum, ref DISPLAY_DEVICE lpDisplayDevice, int dwFlags);
}
