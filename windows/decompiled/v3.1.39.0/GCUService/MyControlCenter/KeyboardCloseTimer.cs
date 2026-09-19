using System;
using System.Diagnostics;
using System.Timers;
using System.Windows.Threading;
using SharpDX.RawInput;

namespace MyControlCenter;

internal class KeyboardCloseTimer
{
	private Stopwatch sw = new Stopwatch();

	private Timer _TimersTimer = new Timer();

	private int _Seconds = 1;

	private int _AccumulationTime;

	private bool _StartMoniter = true;

	private Dispatcher _dispatcher;

	private static readonly KeyboardCloseTimer keyboard = new KeyboardCloseTimer();

	private InputEvents _inputevent;

	public static KeyboardCloseTimer CreateInstance => keyboard;

	public event EventHandler ControlBrigtnessEvent;

	private KeyboardCloseTimer()
	{
		_TimersTimer = new Timer();
		_TimersTimer.Interval = double.MaxValue;
		_TimersTimer.AutoReset = true;
		_TimersTimer.Elapsed += _TimersTimer_Elapsed;
	}

	public void SetDispatcher(Dispatcher dispatcher)
	{
		_dispatcher = dispatcher;
		_dispatcher?.Invoke(delegate
		{
			_inputevent = new InputEvents();
		}, DispatcherPriority.Normal);
	}

	public void HookEvent()
	{
		_dispatcher?.Invoke(delegate
		{
			_inputevent.setEnableDeviceRawInput(enable: true);
			_inputevent.KeyDown -= Input_KeyDown;
			_inputevent.MouseEvent -= Input_MouseEvent;
			_inputevent.KeyDown += Input_KeyDown;
			_inputevent.MouseEvent += Input_MouseEvent;
		}, DispatcherPriority.Normal);
	}

	private void Input_MouseEvent(object sender, MouseInputEventArgs e)
	{
		Keyboard_MouseEventTrigger(e);
	}

	private void Input_KeyDown(object sender, KeyboardInputEventArgs e)
	{
		Keyboard_MouseEventTrigger(e);
	}

	public void UnHookEvent()
	{
		_dispatcher?.Invoke(delegate
		{
			_inputevent.setEnableDeviceRawInput(enable: false);
			_inputevent.KeyDown -= Input_KeyDown;
			_inputevent.MouseEvent -= Input_MouseEvent;
		}, DispatcherPriority.Normal);
	}

	private void Keyboard_MouseEventTrigger(EventArgs e)
	{
		EnableCloseTimer();
		if (this.ControlBrigtnessEvent != null && !_StartMoniter)
		{
			this.ControlBrigtnessEvent(false, null);
			_StartMoniter = true;
		}
	}

	public bool GetStartMoniter()
	{
		return _StartMoniter;
	}

	private void _TimersTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		_AccumulationTime += Convert.ToInt32(_TimersTimer.Interval / 1000.0);
		DisableCloseTimer();
		if (this.ControlBrigtnessEvent != null && _StartMoniter)
		{
			this.ControlBrigtnessEvent(true, null);
			_StartMoniter = false;
		}
	}

	public void SetKeyboardCloseTime(int seconds)
	{
		int result = int.MaxValue;
		int.TryParse(seconds.ToString(), out result);
		if (result != int.MaxValue)
		{
			_Seconds = seconds;
		}
		EnableCloseTimer();
	}

	public void DisableCloseTimer()
	{
		_AccumulationTime = 0;
		_TimersTimer.Stop();
	}

	public void EnableCloseTimer()
	{
		try
		{
			_AccumulationTime = 0;
			if (_Seconds != 0)
			{
				_TimersTimer.Interval = _Seconds * 1000;
			}
			_TimersTimer.Start();
		}
		catch (Exception)
		{
			_AccumulationTime = 0;
			_TimersTimer.Interval = double.MaxValue;
			_TimersTimer.Start();
		}
	}

	internal void Dispose()
	{
		_inputevent?.Dispose();
	}
}
