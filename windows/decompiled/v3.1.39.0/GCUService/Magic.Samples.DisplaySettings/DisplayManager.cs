using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

namespace Magic.Samples.DisplaySettings;

internal static class DisplayManager
{
	public static DisplaySettings GetCurrentSettings(string deviceName)
	{
		return CreateDisplaySettingsObject(-1, GetDeviceMode(deviceName));
	}

	public static void ForceChangeMode(SafeNativeMethods.DEVMODE mode)
	{
		SafeNativeMethods.ChangeDisplaySettings(ref mode, 0u);
	}

	public unsafe static void SetDisplaySettings(string deviceName, SafeNativeMethods.DEVMODE mode)
	{
		SafeNativeMethods.ChangeDisplaySettingsEx(deviceName, ref mode, (IntPtr)(void*)null, SafeNativeMethods.ChangeDisplaySettingsFlags.CDS_UPDATEREGISTRY | SafeNativeMethods.ChangeDisplaySettingsFlags.CDS_SET_PRIMARY | SafeNativeMethods.ChangeDisplaySettingsFlags.CDS_NORESET, IntPtr.Zero);
		SafeNativeMethods.ChangeDisplaySettingsEx(null, IntPtr.Zero, (IntPtr)(void*)null, SafeNativeMethods.ChangeDisplaySettingsFlags.CDS_NONE, (IntPtr)(void*)null);
		string text = null;
		if (text != null)
		{
			throw new InvalidOperationException(text);
		}
	}

	public unsafe static void SetDisplaySettings(DisplaySettings set, string deviceName)
	{
		SafeNativeMethods.DEVMODE lpDevMode = GetDeviceMode(deviceName);
		lpDevMode.dmPelsWidth = (uint)set.Width;
		lpDevMode.dmPelsHeight = (uint)set.Height;
		lpDevMode.dmDisplayOrientation = (uint)set.Orientation;
		lpDevMode.dmBitsPerPel = (uint)set.BitCount;
		lpDevMode.dmDisplayFrequency = (uint)set.Frequency;
		SafeNativeMethods.ChangeDisplaySettingsEx(deviceName, ref lpDevMode, (IntPtr)(void*)null, SafeNativeMethods.ChangeDisplaySettingsFlags.CDS_UPDATEREGISTRY | SafeNativeMethods.ChangeDisplaySettingsFlags.CDS_SET_PRIMARY | SafeNativeMethods.ChangeDisplaySettingsFlags.CDS_NORESET, IntPtr.Zero);
		SafeNativeMethods.ChangeDisplaySettingsEx(null, IntPtr.Zero, (IntPtr)(void*)null, SafeNativeMethods.ChangeDisplaySettingsFlags.CDS_NONE, (IntPtr)(void*)null);
		string text = null;
		if (text != null)
		{
			throw new InvalidOperationException(text);
		}
	}

	public static List<DisplaySettings> GetModesEnumerator()
	{
		SafeNativeMethods.DEVMODE lpDevMode = default(SafeNativeMethods.DEVMODE);
		lpDevMode.Initialize();
		int iModeNum = 0;
		List<DisplaySettings> list = new List<DisplaySettings>();
		while (SafeNativeMethods.EnumDisplaySettings(null, iModeNum, ref lpDevMode))
		{
			list.Add(CreateDisplaySettingsObject(iModeNum++, lpDevMode));
		}
		return list;
	}

	public static void RotateScreen(bool clockwise)
	{
	}

	private static DisplaySettings CreateDisplaySettingsObject(int idx, SafeNativeMethods.DEVMODE mode)
	{
		return new DisplaySettings
		{
			Index = idx,
			mode = mode,
			DeviceName = mode.dmDeviceName,
			Width = (int)mode.dmPelsWidth,
			Height = (int)mode.dmPelsHeight,
			Orientation = (Orientation)mode.dmDisplayOrientation,
			BitCount = (int)mode.dmBitsPerPel,
			Frequency = (int)mode.dmDisplayFrequency
		};
	}

	private static SafeNativeMethods.DEVMODE GetDeviceMode(string devicename)
	{
		SafeNativeMethods.DEVMODE lpDevMode = default(SafeNativeMethods.DEVMODE);
		lpDevMode.Initialize();
		if (SafeNativeMethods.EnumDisplaySettings(devicename, -1, ref lpDevMode))
		{
			return lpDevMode;
		}
		throw new InvalidOperationException(GetLastError());
	}

	public static IEnumerable<SafeNativeMethods.DEVMODE> EnumerateCompatibleModes(string deviceName)
	{
		SafeNativeMethods.DEVMODE devMode = new SafeNativeMethods.DEVMODE
		{
			dmSize = (ushort)Marshal.SizeOf(typeof(SafeNativeMethods.DEVMODE))
		};
		for (int index = 0; SafeNativeMethods.EnumDisplaySettings(deviceName, index, ref devMode); index++)
		{
			yield return devMode;
		}
	}

	private static string GetLastError()
	{
		int lastWin32Error = Marshal.GetLastWin32Error();
		if (SafeNativeMethods.FormatMessage(4864u, 2048u, (uint)lastWin32Error, 0u, out var lpBuffer, 0u, 0u) == 0)
		{
			return "InvalidOperation_FatalError";
		}
		return lpBuffer;
	}
}
