using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
using Utility;

namespace MyControlCenter.MySetting.ColorCalibration;

internal class ColorProfileControl
{
	[Flags]
	private enum DisplayDeviceStateFlags : uint
	{
		AttachedToDesktop = 1u,
		MultiDriver = 2u,
		PrimaryDevice = 4u,
		MirroringDriver = 8u,
		VGACompatible = 0x10u,
		Removable = 0x20u,
		ModesPruned = 0x8000000u,
		Remote = 0x4000000u,
		Disconnect = 0x2000000u,
		Active = 1u,
		Attached = 2u
	}

	private enum DeviceClassFlags : uint
	{
		CLASS_MONITOR = 1835955314u,
		CLASS_PRINTER = 1886549106u,
		CLASS_SCANNER = 1935896178u
	}

	private enum WCS_PROFILE_MANAGEMENT_SCOPE : uint
	{
		WCS_PROFILE_MANAGEMENT_SCOPE_SYSTEM_WIDE,
		WCS_PROFILE_MANAGEMENT_SCOPE_CURRENT_USER
	}

	private enum COLORPROFILETYPE : uint
	{
		CPT_ICC,
		CPT_DMP,
		CPT_CAMP,
		CPT_GMMP
	}

	private enum COLORPROFILESUBTYPE : uint
	{
		CPST_PERCEPTUAL,
		CPST_RELATIVE_COLORIMETRIC,
		CPST_SATURATION,
		CPST_ABSOLUTE_COLORIMETRIC,
		CPST_NONE,
		CPST_RGB_WORKING_SPACE,
		CPST_CUSTOM_WORKING_SPACE
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
	private struct DISPLAY_DEVICE
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

	private const uint EDD_GET_DEVICE_INTERFACE_NAME = 1u;

	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	private static extern uint EnumDisplayDevices(string s, uint iDevNum, ref DISPLAY_DEVICE displayDevice, uint dwFlags);

	[DllImport("Mscms.dll", CharSet = CharSet.Unicode, SetLastError = true)]
	private static extern uint WcsGetUsePerUserProfiles(string deviceName, DeviceClassFlags deviceClass, out uint usePerUserProfiles);

	[DllImport("Mscms.dll", CharSet = CharSet.Unicode, SetLastError = true)]
	private static extern uint WcsSetUsePerUserProfiles(string deviceName, DeviceClassFlags deviceClass, uint usePerUserProfiles);

	[DllImport("Mscms.dll", CharSet = CharSet.Unicode, SetLastError = true)]
	private static extern uint WcsGetDefaultColorProfileSize(WCS_PROFILE_MANAGEMENT_SCOPE scope, string deviceName, COLORPROFILETYPE colorProfileType, COLORPROFILESUBTYPE colorProfileSubType, uint dwProfileID, out uint cbProfileName);

	[DllImport("Mscms.dll", CharSet = CharSet.Unicode, SetLastError = true)]
	private static extern uint WcsGetDefaultColorProfile(WCS_PROFILE_MANAGEMENT_SCOPE scope, string deviceName, COLORPROFILETYPE colorProfileType, COLORPROFILESUBTYPE colorProfileSubType, uint dwProfileID, uint cbProfileName, StringBuilder profileName);

	[DllImport("Mscms.dll", CharSet = CharSet.Unicode, SetLastError = true)]
	private static extern bool WcsSetDefaultColorProfile(WCS_PROFILE_MANAGEMENT_SCOPE scope, string deviceName, COLORPROFILETYPE colorProfileType, COLORPROFILESUBTYPE colorProfileSubType, uint dwProfileID, string cbProfileName);

	[DllImport("Mscms.dll", CharSet = CharSet.Unicode, SetLastError = true)]
	private static extern bool WcsDisassociateColorProfileFromDevice(WCS_PROFILE_MANAGEMENT_SCOPE scope, string cbProfileName, string deviceName);

	[DllImport("Mscms.dll")]
	public static extern bool WcsGetCalibrationManagementState(out bool pbIsEnabled);

	[DllImport("Mscms.dll")]
	public static extern bool WcsSetCalibrationManagementState(in bool pbIsEnabled);

	[DllImport("Mscms.dll")]
	public static extern bool InstallColorProfile(IntPtr hdc, string path);

	[DllImport("Mscms.dll")]
	public static extern bool UninstallColorProfile(IntPtr hdc, string path, bool bDelete);

	[DllImport("Mscms.dll")]
	public static extern bool AssociateColorProfileWithDeviceA(IntPtr hdc, string path, string device);

	[DllImport("gdi32")]
	public static extern int SetICMMode(IntPtr hdc, int n);

	[DllImport("gdi32.dll", SetLastError = true)]
	private static extern bool SetICMProfileA(IntPtr hDC, string lpFileName);

	[DllImport("user32.dll", ExactSpelling = true)]
	public static extern IntPtr GetDC(IntPtr hWnd);

	[DllImport("gdi32.dll")]
	private static extern IntPtr CreateDC(string lpszDriver, string lpszDevice, string lpszOutput, IntPtr lpInitData);

	public void SetCalibrationState(bool Enable)
	{
		WcsSetCalibrationManagementState(in Enable);
	}

	public static bool GetCalibrationState()
	{
		WcsGetCalibrationManagementState(out var pbIsEnabled);
		return pbIsEnabled;
	}

	public void InstallProfile(string fullPath)
	{
		LogCtrl.Write("[InstallProfile] Result: " + InstallColorProfile(IntPtr.Zero, fullPath));
	}

	public void UnInstallProfile(string fullPath, bool bDelete)
	{
		LogCtrl.Write("[UnInstallProfile] Result: " + UninstallColorProfile(IntPtr.Zero, fullPath, bDelete));
	}

	public unsafe static void AssoiateWithDevice(string filename)
	{
		try
		{
			DISPLAY_DEVICE displayDevice = default(DISPLAY_DEVICE);
			displayDevice.cb = Marshal.SizeOf(displayDevice);
			string s = null;
			string text = null;
			uint num = 0u;
			while (EnumDisplayDevices(null, num++, ref displayDevice, 1u) != 0)
			{
				if ((displayDevice.StateFlags & DisplayDeviceStateFlags.AttachedToDesktop) != 0 && (displayDevice.StateFlags & DisplayDeviceStateFlags.PrimaryDevice) != 0)
				{
					s = displayDevice.DeviceName;
					break;
				}
			}
			num = 0u;
			while (EnumDisplayDevices(s, num++, ref displayDevice, 1u) != 0)
			{
				if ((displayDevice.StateFlags & DisplayDeviceStateFlags.AttachedToDesktop) != 0 && (displayDevice.StateFlags & DisplayDeviceStateFlags.MultiDriver) != 0)
				{
					text = displayDevice.DeviceString;
					break;
				}
			}
			CreateDC("DISPLAY", text, null, (IntPtr)(void*)null);
			AssociateColorProfileWithDeviceA(IntPtr.Zero, filename, text);
		}
		catch (Exception ex)
		{
			Console.WriteLine($"{ex.ToString()}");
		}
	}

	public bool SetMonitorProfile(string newprofileName)
	{
		bool flag = false;
		DISPLAY_DEVICE displayDevice = default(DISPLAY_DEVICE);
		displayDevice.cb = Marshal.SizeOf(displayDevice);
		LogCtrl.Write("[SetMonitorProfile] First, find the primary adaptor.");
		string s = null;
		uint num = 0u;
		while (EnumDisplayDevices(null, num++, ref displayDevice, 1u) != 0)
		{
			if ((displayDevice.StateFlags & DisplayDeviceStateFlags.AttachedToDesktop) != 0 && (displayDevice.StateFlags & DisplayDeviceStateFlags.PrimaryDevice) != 0)
			{
				s = displayDevice.DeviceName;
				break;
			}
		}
		LogCtrl.Write("[SetMonitorProfile] Second, find the first active (and attached) monitor.");
		string deviceName = null;
		num = 0u;
		while (EnumDisplayDevices(s, num++, ref displayDevice, 1u) != 0)
		{
			if ((displayDevice.StateFlags & DisplayDeviceStateFlags.AttachedToDesktop) != 0 && (displayDevice.StateFlags & DisplayDeviceStateFlags.MultiDriver) != 0)
			{
				deviceName = displayDevice.DeviceKey;
				break;
			}
		}
		LogCtrl.Write("[SetMonitorProfile] Forced to enalbe the user setting.");
		uint usePerUserProfiles = 0u;
		WcsSetUsePerUserProfiles(deviceName, DeviceClassFlags.CLASS_MONITOR, usePerUserProfiles);
		LogCtrl.Write("[SetMonitorProfile] Third, find out whether to use the global or user profile.");
		usePerUserProfiles = 0u;
		if (WcsGetUsePerUserProfiles(deviceName, DeviceClassFlags.CLASS_MONITOR, out usePerUserProfiles) == 0)
		{
			LogCtrl.Write("[SetMonitorProfile] res = 0");
			throw new Win32Exception(Marshal.GetLastWin32Error());
		}
		LogCtrl.Write("[SetMonitorProfile] Finally, get the profile name.");
		flag = WcsSetDefaultColorProfile(WCS_PROFILE_MANAGEMENT_SCOPE.WCS_PROFILE_MANAGEMENT_SCOPE_SYSTEM_WIDE, deviceName, COLORPROFILETYPE.CPT_ICC, COLORPROFILESUBTYPE.CPST_RGB_WORKING_SPACE, 0u, newprofileName);
		LogCtrl.Write("[SetMonitorProfile] WcsSetDefaultColorProfile setRes=" + flag);
		return flag;
	}

	public bool DissociateProfile(string newprofileName)
	{
		DISPLAY_DEVICE displayDevice = default(DISPLAY_DEVICE);
		displayDevice.cb = Marshal.SizeOf(displayDevice);
		string s = null;
		uint num = 0u;
		while (EnumDisplayDevices(null, num++, ref displayDevice, 1u) != 0)
		{
			if ((displayDevice.StateFlags & DisplayDeviceStateFlags.AttachedToDesktop) != 0 && (displayDevice.StateFlags & DisplayDeviceStateFlags.PrimaryDevice) != 0)
			{
				s = displayDevice.DeviceName;
				break;
			}
		}
		string deviceName = null;
		num = 0u;
		while (EnumDisplayDevices(s, num++, ref displayDevice, 1u) != 0)
		{
			if ((displayDevice.StateFlags & DisplayDeviceStateFlags.AttachedToDesktop) != 0 && (displayDevice.StateFlags & DisplayDeviceStateFlags.MultiDriver) != 0)
			{
				deviceName = displayDevice.DeviceKey;
				break;
			}
		}
		return WcsDisassociateColorProfileFromDevice(WCS_PROFILE_MANAGEMENT_SCOPE.WCS_PROFILE_MANAGEMENT_SCOPE_SYSTEM_WIDE, newprofileName, deviceName);
	}

	public string GetMonitorProfile()
	{
		DISPLAY_DEVICE displayDevice = default(DISPLAY_DEVICE);
		displayDevice.cb = Marshal.SizeOf(displayDevice);
		string s = null;
		uint num = 0u;
		while (EnumDisplayDevices(null, num++, ref displayDevice, 1u) != 0)
		{
			if ((displayDevice.StateFlags & DisplayDeviceStateFlags.AttachedToDesktop) != 0 && (displayDevice.StateFlags & DisplayDeviceStateFlags.PrimaryDevice) != 0)
			{
				s = displayDevice.DeviceName;
				break;
			}
		}
		string deviceName = null;
		num = 0u;
		while (EnumDisplayDevices(s, num++, ref displayDevice, 1u) != 0)
		{
			if ((displayDevice.StateFlags & DisplayDeviceStateFlags.AttachedToDesktop) != 0 && (displayDevice.StateFlags & DisplayDeviceStateFlags.MultiDriver) != 0)
			{
				deviceName = displayDevice.DeviceKey;
				break;
			}
		}
		uint usePerUserProfiles = 0u;
		if (WcsGetUsePerUserProfiles(deviceName, DeviceClassFlags.CLASS_MONITOR, out usePerUserProfiles) == 0)
		{
			throw new Win32Exception(Marshal.GetLastWin32Error());
		}
		int scope = ((usePerUserProfiles != 0) ? 1 : 0);
		uint cbProfileName = 0u;
		if (WcsGetDefaultColorProfileSize((WCS_PROFILE_MANAGEMENT_SCOPE)scope, deviceName, COLORPROFILETYPE.CPT_ICC, COLORPROFILESUBTYPE.CPST_RGB_WORKING_SPACE, 0u, out cbProfileName) == 0)
		{
			throw new Win32Exception(Marshal.GetLastWin32Error());
		}
		StringBuilder stringBuilder = new StringBuilder((int)cbProfileName / 2);
		if (WcsGetDefaultColorProfile((WCS_PROFILE_MANAGEMENT_SCOPE)scope, deviceName, COLORPROFILETYPE.CPT_ICC, COLORPROFILESUBTYPE.CPST_RGB_WORKING_SPACE, 0u, cbProfileName, stringBuilder) == 0)
		{
			throw new Win32Exception(Marshal.GetLastWin32Error());
		}
		return stringBuilder.ToString();
	}

	[DllImport("Mscms.dll", CharSet = CharSet.Unicode, SetLastError = true)]
	private static extern bool GetColorDirectory(IntPtr pMachineName, StringBuilder pBuffer, ref uint pdwSize);

	public static string GetColorDirectory()
	{
		uint pdwSize = 260u;
		StringBuilder stringBuilder = new StringBuilder((int)pdwSize);
		if (GetColorDirectory(IntPtr.Zero, stringBuilder, ref pdwSize))
		{
			return stringBuilder.ToString();
		}
		throw new Win32Exception(Marshal.GetLastWin32Error());
	}
}
