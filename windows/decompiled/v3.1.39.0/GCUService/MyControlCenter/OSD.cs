using System;
using System.CodeDom.Compiler;
using System.ComponentModel;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using System.Timers;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Shapes;

namespace MyControlCenter;

public class OSD : Window, IComponentConnector
{
	[Flags]
	public enum ExtendedWindowStyles
	{
		WS_EX_TOOLWINDOW = 0x80,
		WS_EX_NOACTIVATE = 0x8000000
	}

	public enum GetWindowLongFields
	{
		GWL_EXSTYLE = -20
	}

	private delegate void CloseWindow(Window window);

	private Timer CloseTimer;

	private object _objLock = new object();

	internal OSD OSDWindow;

	internal DockPanel OSDDockPanel;

	internal Grid OSDDockGrid;

	internal Rectangle OSDBackRectangle;

	internal Image img;

	internal StackPanel OSDTextStackPanel;

	internal TextBlock OSDText1;

	internal TextBlock OSDText2;

	private bool _contentLoaded;

	[DllImport("user32.dll")]
	public static extern IntPtr GetWindowLong(IntPtr hWnd, int nIndex);

	public static IntPtr SetWindowLong(IntPtr hWnd, int nIndex, IntPtr dwNewLong)
	{
		int num = 0;
		IntPtr zero = IntPtr.Zero;
		SetLastError(0);
		if (IntPtr.Size == 4)
		{
			int value = IntSetWindowLong(hWnd, nIndex, IntPtrToInt32(dwNewLong));
			num = Marshal.GetLastWin32Error();
			zero = new IntPtr(value);
		}
		else
		{
			zero = IntSetWindowLongPtr(hWnd, nIndex, dwNewLong);
			num = Marshal.GetLastWin32Error();
		}
		if (zero == IntPtr.Zero && num != 0)
		{
			throw new Win32Exception(num);
		}
		return zero;
	}

	[DllImport("user32.dll", EntryPoint = "SetWindowLongPtr", SetLastError = true)]
	private static extern IntPtr IntSetWindowLongPtr(IntPtr hWnd, int nIndex, IntPtr dwNewLong);

	[DllImport("user32.dll", EntryPoint = "SetWindowLong", SetLastError = true)]
	private static extern int IntSetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);

	private static int IntPtrToInt32(IntPtr intPtr)
	{
		return (int)intPtr.ToInt64();
	}

	[DllImport("kernel32.dll")]
	public static extern void SetLastError(int dwErrorCode);

	public OSD()
	{
		InitializeComponent();
		StartCloseTimer();
	}

	public OSD(int OsdWidth)
	{
		InitializeComponent();
		if (OsdWidth > 0)
		{
			OSDDockGrid.Width = OsdWidth;
		}
		StartCloseTimer();
	}

	private void StartCloseTimer()
	{
		CloseTimer = new Timer();
		CloseTimer.Interval = 3000.0;
		CloseTimer.Elapsed += CloseTimer_Elapsed;
		CloseTimer.Start();
	}

	public void SetOSDString(string osdString1, string osdString2, double opacity1, double opacity2)
	{
		OSDText1.Text = osdString1;
		OSDText2.Text = osdString2;
		OSDText1.Opacity = opacity1;
		OSDText2.Opacity = opacity2;
	}

	private void CloseTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		base.Dispatcher.BeginInvoke(new CloseWindow(_mCloseWindow), this);
	}

	private void _mCloseWindow(Window window)
	{
		lock (_objLock)
		{
			CloseTimer.Stop();
			CloseTimer.Dispose();
			window.Close();
		}
	}

	private void Window_Loaded(object sender, RoutedEventArgs e)
	{
		WindowInteropHelper windowInteropHelper = new WindowInteropHelper(this);
		int num = (int)GetWindowLong(windowInteropHelper.Handle, -20);
		num |= 0x80;
		num |= 0x8000000;
		SetWindowLong(windowInteropHelper.Handle, -20, (IntPtr)num);
	}

	internal void SetOSDColor(Color OSDDefaultColor)
	{
		SolidColorBrush solidColorBrush = new SolidColorBrush();
		solidColorBrush.Color = Color.FromArgb(100, OSDDefaultColor.R, OSDDefaultColor.G, OSDDefaultColor.B);
		(OSDBackRectangle.Stroke as GradientBrush).GradientStops.Last().Color = solidColorBrush.Color;
		(OSDBackRectangle.Fill as GradientBrush).GradientStops.Last().Color = solidColorBrush.Color;
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
	public void InitializeComponent()
	{
		if (!_contentLoaded)
		{
			_contentLoaded = true;
			Uri resourceLocator = new Uri("/GCUService;component/osd/osd.xaml", UriKind.Relative);
			Application.LoadComponent(this, resourceLocator);
		}
	}

	void IComponentConnector.InitializeComponent()
	{
		//ILSpy generated this explicit interface implementation from .override directive in InitializeComponent
		this.InitializeComponent();
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
	[EditorBrowsable(EditorBrowsableState.Never)]
	void IComponentConnector.Connect(int connectionId, object target)
	{
		switch (connectionId)
		{
		case 1:
			OSDWindow = (OSD)target;
			OSDWindow.Loaded += Window_Loaded;
			break;
		case 2:
			OSDDockPanel = (DockPanel)target;
			break;
		case 3:
			OSDDockGrid = (Grid)target;
			break;
		case 4:
			OSDBackRectangle = (Rectangle)target;
			break;
		case 5:
			img = (Image)target;
			break;
		case 6:
			OSDTextStackPanel = (StackPanel)target;
			break;
		case 7:
			OSDText1 = (TextBlock)target;
			break;
		case 8:
			OSDText2 = (TextBlock)target;
			break;
		default:
			_contentLoaded = true;
			break;
		}
	}
}
