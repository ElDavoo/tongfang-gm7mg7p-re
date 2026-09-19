using System;
using System.Runtime.InteropServices;

namespace Utility;

internal class CreateProcessAsUserWrapper
{
	private enum WTS_CONNECTSTATE_CLASS
	{
		WTSActive,
		WTSConnected,
		WTSConnectQuery,
		WTSShadow,
		WTSDisconnected,
		WTSIdle,
		WTSListen,
		WTSReset,
		WTSDown,
		WTSInit
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	private struct WTS_SESSION_INFO
	{
		public uint SessionID;

		public string pWinStationName;

		public WTS_CONNECTSTATE_CLASS State;
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	private struct STARTUPINFO
	{
		public int cb;

		public string lpReserved;

		public string lpDesktop;

		public string lpTitle;

		public int dwX;

		public int dwY;

		public int dwXSize;

		public int dwYSize;

		public int dwXCountChars;

		public int dwYCountChars;

		public int dwFillAttribute;

		public int dwFlags;

		public short wShowWindow;

		public short cbReserved2;

		public IntPtr lpReserved2;

		public IntPtr hStdInput;

		public IntPtr hStdOutput;

		public IntPtr hStdError;
	}

	[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
	private struct PROCESS_INFORMATION
	{
		public IntPtr hProcess;

		public IntPtr hThread;

		public int dwProcessId;

		public int dwThreadId;
	}

	private const int WTS_CURRENT_SERVER_HANDLE = 0;

	public static void LaunchChildProcess(string ChildProcName)
	{
		IntPtr ppSessionInfo = IntPtr.Zero;
		uint pSessionInfoCount = 0u;
		if (!WTSEnumerateSessions((IntPtr)0, 0u, 1u, ref ppSessionInfo, ref pSessionInfoCount))
		{
			return;
		}
		for (int i = 0; i < pSessionInfoCount; i++)
		{
			WTS_SESSION_INFO wTS_SESSION_INFO = (WTS_SESSION_INFO)Marshal.PtrToStructure(ppSessionInfo + i * Marshal.SizeOf(typeof(WTS_SESSION_INFO)), typeof(WTS_SESSION_INFO));
			if (wTS_SESSION_INFO.State != WTS_CONNECTSTATE_CLASS.WTSActive)
			{
				continue;
			}
			IntPtr Token = IntPtr.Zero;
			if (WTSQueryUserToken(wTS_SESSION_INFO.SessionID, out Token))
			{
				STARTUPINFO lpStartupInfo = new STARTUPINFO
				{
					cb = Marshal.SizeOf(typeof(STARTUPINFO))
				};
				if (CreateProcessAsUser(Token, ChildProcName, null, IntPtr.Zero, IntPtr.Zero, bInheritHandles: false, 0u, null, null, ref lpStartupInfo, out var lpProcessInformation))
				{
					CloseHandle(lpProcessInformation.hThread);
					CloseHandle(lpProcessInformation.hProcess);
				}
				CloseHandle(Token);
				break;
			}
		}
		WTSFreeMemory(ppSessionInfo);
	}

	[DllImport("WTSAPI32.DLL", CharSet = CharSet.Auto, SetLastError = true)]
	private static extern bool WTSEnumerateSessions(IntPtr hServer, [MarshalAs(UnmanagedType.U4)] uint Reserved, [MarshalAs(UnmanagedType.U4)] uint Version, ref IntPtr ppSessionInfo, [MarshalAs(UnmanagedType.U4)] ref uint pSessionInfoCount);

	[DllImport("WTSAPI32.DLL", CharSet = CharSet.Auto, SetLastError = true)]
	private static extern void WTSFreeMemory(IntPtr pMemory);

	[DllImport("WTSAPI32.DLL", CharSet = CharSet.Auto, SetLastError = true)]
	private static extern bool WTSQueryUserToken(uint sessionId, out IntPtr Token);

	[DllImport("ADVAPI32.DLL", CharSet = CharSet.Auto, SetLastError = true)]
	private static extern bool CreateProcessAsUser(IntPtr hToken, string lpApplicationName, string lpCommandLine, IntPtr lpProcessAttributes, IntPtr lpThreadAttributes, bool bInheritHandles, uint dwCreationFlags, string lpEnvironment, string lpCurrentDirectory, ref STARTUPINFO lpStartupInfo, out PROCESS_INFORMATION lpProcessInformation);

	[DllImport("KERNEL32.DLL", CharSet = CharSet.Auto, SetLastError = true)]
	private static extern bool CloseHandle(IntPtr hHandle);
}
