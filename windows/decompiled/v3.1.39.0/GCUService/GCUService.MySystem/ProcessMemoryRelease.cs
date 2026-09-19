using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace GCUService.MySystem;

internal class ProcessMemoryRelease
{
	[DllImport("kernel32.dll")]
	private static extern bool SetProcessWorkingSetSize(IntPtr proc, int min, int max);

	public void Release(Process process)
	{
		SetProcessWorkingSetSize(process.Handle, -1, -1);
	}
}
