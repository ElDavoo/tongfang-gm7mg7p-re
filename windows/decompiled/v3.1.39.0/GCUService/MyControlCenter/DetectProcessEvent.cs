using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Timers;

namespace MyControlCenter;

internal class DetectProcessEvent
{
	private static readonly DetectProcessEvent model = new DetectProcessEvent();

	private static HashSet<string> PairedApplicationNames = new HashSet<string>();

	private Timer _TimersTimer = new Timer();

	private bool IsFocused;

	private string oldProcess = string.Empty;

	public static DetectProcessEvent CreateInstance => model;

	public event EventHandler OnForegroundProcessEvent;

	[DllImport("user32.dll")]
	private static extern IntPtr GetForegroundWindow();

	[DllImport("user32.dll")]
	private static extern int GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

	public void AddPairedApplication(string name)
	{
		if (name != null)
		{
			PairedApplicationNames.Add(name);
		}
	}

	public void RemovePairedApplication(string name)
	{
		if (name != null)
		{
			PairedApplicationNames.Remove(name);
		}
	}

	public void ClearPairedApplicationAll()
	{
		if (PairedApplicationNames != null)
		{
			PairedApplicationNames.Clear();
		}
	}

	public void StartPairedApplicationMonitor()
	{
		_TimersTimer.Start();
	}

	public void StopPairedApplicationMonitor()
	{
		_TimersTimer.Stop();
	}
}
