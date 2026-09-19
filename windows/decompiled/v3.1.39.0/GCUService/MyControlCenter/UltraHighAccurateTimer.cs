using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Threading;

namespace MyControlCenter;

internal class UltraHighAccurateTimer
{
	public delegate void ManualTimerEventHandler(object sender);

	private long clockFrequency;

	private bool running;

	private Thread timerThread;

	private int intervalMs;

	private long intevalTicks;

	public int Interval
	{
		get
		{
			return intervalMs;
		}
		set
		{
			intervalMs = value;
			intevalTicks = (long)((double)value * (double)clockFrequency / 1000.0);
		}
	}

	public event ManualTimerEventHandler Tick;

	[DllImport("Kernel32.dll")]
	private static extern bool QueryPerformanceCounter(out long lpPerformanceCount);

	[DllImport("Kernel32.dll")]
	private static extern bool QueryPerformanceFrequency(out long lpFrequency);

	public UltraHighAccurateTimer()
	{
		if (!QueryPerformanceFrequency(out clockFrequency))
		{
			throw new Win32Exception("QueryPerformanceFrequency() function is not supported");
		}
	}

	private void ThreadProc()
	{
		GetTick(out var currentTickCount);
		long num = currentTickCount + intevalTicks;
		while (running)
		{
			while (currentTickCount < num)
			{
				GetTick(out currentTickCount);
			}
			num = currentTickCount + intevalTicks;
			if (this.Tick != null)
			{
				this.Tick(this);
			}
		}
	}

	public bool GetTick(out long currentTickCount)
	{
		if (!QueryPerformanceCounter(out currentTickCount))
		{
			throw new Win32Exception("QueryPerformanceCounter() failed!");
		}
		return true;
	}

	public void Start()
	{
		running = false;
		timerThread?.Abort();
		running = true;
		timerThread = new Thread(ThreadProc);
		timerThread.Name = "HighAccuracyTimer";
		timerThread.Priority = ThreadPriority.Highest;
		timerThread.Start();
	}

	public void Stop()
	{
		running = false;
		timerThread?.Abort();
	}

	~UltraHighAccurateTimer()
	{
		running = false;
		timerThread?.Abort();
	}
}
