using System;
using System.Runtime.InteropServices;

namespace LightingModel;

public static class MusicMode
{
	[UnmanagedFunctionPointer(CallingConvention.Winapi)]
	internal delegate bool STARTMONITORAUDIO(ushort nParam, byte bLight);

	[UnmanagedFunctionPointer(CallingConvention.Winapi)]
	internal delegate void STOPMONITORAUDIO();

	internal static IntPtr m_hAudio = LoadLibrary("audiostealer.dll");

	internal static IntPtr m_pStartMonitorAudio = GetProcAddress(m_hAudio, "StartMonitorAudio");

	internal static IntPtr m_pStopMonitorAudio = GetProcAddress(m_hAudio, "StopMonitorAudio");

	internal static STARTMONITORAUDIO m_delStartMonitorAudio = (STARTMONITORAUDIO)Marshal.GetDelegateForFunctionPointer(m_pStartMonitorAudio, typeof(STARTMONITORAUDIO));

	internal static STOPMONITORAUDIO m_delStopMonitorAudio = (STOPMONITORAUDIO)Marshal.GetDelegateForFunctionPointer(m_pStopMonitorAudio, typeof(STOPMONITORAUDIO));

	[DllImport("kernel32.dll")]
	internal static extern IntPtr LoadLibrary(string dllToLoad);

	[DllImport("kernel32.dll")]
	internal static extern IntPtr GetProcAddress(IntPtr hModule, string procedureName);

	[DllImport("kernel32.dll")]
	internal static extern bool FreeLibrary(IntPtr hModule);
}
