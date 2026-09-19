using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Windows.Forms;
using Microsoft.Win32;
using SharpDX.Multimedia;
using SharpDX.RawInput;
using Utility;

namespace MyControlCenter;

public sealed class InputEvents : IDisposable
{
	private sealed class DisposableRawInputHook : IDisposable
	{
		private IntPtr _target;

		private readonly UsagePage usagePage;

		private readonly UsageId usageIdKeyboard;

		private readonly UsageId usageIdMouse;

		private readonly UsageId usageIdTouchpad;

		private readonly EventHandler<KeyboardInputEventArgs> keyHandler;

		private readonly EventHandler<MouseInputEventArgs> mouseHandler;

		private readonly EventHandler<RawInputEventArgs> rawHandler;

		public void OnlyRemoveInput()
		{
			Device.KeyboardInput -= keyHandler;
			Device.RegisterDevice(usagePage, usageIdKeyboard, DeviceFlags.Remove);
			Device.MouseInput -= mouseHandler;
			Device.RegisterDevice(usagePage, usageIdMouse, DeviceFlags.Remove);
		}

		public void OnlyAddInput()
		{
			Device.RegisterDevice(usagePage, usageIdKeyboard, DeviceFlags.InputSink, _target);
			Device.KeyboardInput += keyHandler;
			Device.RegisterDevice(usagePage, usageIdMouse, DeviceFlags.InputSink, _target);
			Device.MouseInput += mouseHandler;
		}

		public DisposableRawInputHook(UsagePage usagePage, UsageId usageIdKeyboard, UsageId usageIdMouse, DeviceFlags flags, IntPtr target, EventHandler<KeyboardInputEventArgs> keyHandler, EventHandler<MouseInputEventArgs> mouseHandler)
		{
			_target = target;
			this.usagePage = usagePage;
			this.usageIdKeyboard = usageIdKeyboard;
			this.usageIdMouse = usageIdMouse;
			this.keyHandler = keyHandler;
			this.mouseHandler = mouseHandler;
			Device.RegisterDevice(usagePage, usageIdKeyboard, flags, target);
			Device.KeyboardInput += keyHandler;
			Device.RegisterDevice(usagePage, usageIdMouse, flags, target);
			Device.MouseInput += mouseHandler;
		}

		public void Dispose()
		{
			Device.KeyboardInput -= keyHandler;
			Device.RegisterDevice(usagePage, usageIdKeyboard, DeviceFlags.Remove);
			Device.MouseInput -= mouseHandler;
			Device.RegisterDevice(usagePage, usageIdMouse, DeviceFlags.Remove);
		}

		void IDisposable.Dispose()
		{
			//ILSpy generated this explicit interface implementation from .override directive in Dispose
			this.Dispose();
		}
	}

	private readonly MessagePumpThread thread = new MessagePumpThread();

	private readonly List<Keys> pressedKeySequence = new List<Keys>();

	private readonly List<MouseButtons> pressedMouseButtons = new List<MouseButtons>();

	private DisposableRawInputHook _rawHook;

	private bool disposed;

	public Keys[] PressedKeys => pressedKeySequence.ToArray();

	public MouseButtons[] PressedButtons => pressedMouseButtons.ToArray();

	public bool Shift => new Keys[3]
	{
		Keys.ShiftKey,
		Keys.RShiftKey,
		Keys.LShiftKey
	}.Any(((IEnumerable<Keys>)PressedKeys).Contains<Keys>);

	public bool Alt => new Keys[3]
	{
		Keys.Menu,
		Keys.RMenu,
		Keys.LMenu
	}.Any(((IEnumerable<Keys>)PressedKeys).Contains<Keys>);

	public bool Control => new Keys[3]
	{
		Keys.ControlKey,
		Keys.RControlKey,
		Keys.LControlKey
	}.Any(((IEnumerable<Keys>)PressedKeys).Contains<Keys>);

	public bool Windows => new Keys[2]
	{
		Keys.LWin,
		Keys.RWin
	}.Any(((IEnumerable<Keys>)PressedKeys).Contains<Keys>);

	public event EventHandler<KeyboardInputEventArgs> KeyDown;

	public event EventHandler<KeyboardInputEventArgs> KeyUp;

	public event EventHandler<MouseInputEventArgs> MouseEvent;

	public InputEvents()
	{
		try
		{
			thread.Start(MessagePumpInit);
			SystemEvents.SessionSwitch += SystemEvents_SessionSwitch;
		}
		catch
		{
			Dispose();
			throw;
		}
	}

	private void SystemEvents_SessionSwitch(object sender, SessionSwitchEventArgs e)
	{
		if (e.Reason == SessionSwitchReason.SessionLock || e.Reason == SessionSwitchReason.SessionUnlock)
		{
			pressedKeySequence.Clear();
		}
	}

	public void setEnableDeviceRawInput(bool enable)
	{
		if (enable)
		{
			_rawHook.OnlyAddInput();
		}
		else
		{
			_rawHook.OnlyRemoveInput();
		}
	}

	private void MessagePumpInit()
	{
		using Form form = new Form();
		_rawHook = new DisposableRawInputHook(UsagePage.Generic, UsageId.GenericKeyboard, UsageId.GenericMouse, DeviceFlags.InputSink, form.Handle, DeviceOnKeyboardInput, DeviceOnMouseInput);
		using (_rawHook)
		{
			thread.EnterMessageLoop();
		}
	}

	private void DeviceOnKeyboardInput(object sender, KeyboardInputEventArgs e)
	{
		if (e.Key == (Keys.F16 | Keys.F17) && e.Key != (Keys.F16 | Keys.F17))
		{
			return;
		}
		try
		{
			if (e.ScanCodeFlags.HasFlag(ScanCodeFlags.Break))
			{
				pressedKeySequence.RemoveAll((Keys k) => k == e.Key);
				this.KeyUp?.Invoke(sender, e);
				return;
			}
			if (!pressedKeySequence.Contains(e.Key))
			{
				pressedKeySequence.Add(e.Key);
			}
			this.KeyDown?.Invoke(sender, e);
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Exception while handling keyboard input. Error: " + ex.ToString());
		}
	}

	private void DeviceOnMouseInput(object sender, MouseInputEventArgs e)
	{
		try
		{
			this.MouseEvent?.Invoke(sender, e);
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Exception while handling mouse input. Error: " + ex.ToString());
		}
	}

	private void DeviceOnRawInput(object sender, RawInputEventArgs e)
	{
		try
		{
			foreach (PropertyDescriptor property in TypeDescriptor.GetProperties(e))
			{
				_ = property.Name;
				property.GetValue(e);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Exception while handling mouse input. Error: " + ex.ToString());
		}
	}

	public void Dispose()
	{
		if (!disposed)
		{
			disposed = true;
			thread.Dispose();
		}
	}

	void IDisposable.Dispose()
	{
		//ILSpy generated this explicit interface implementation from .override directive in Dispose
		this.Dispose();
	}
}
