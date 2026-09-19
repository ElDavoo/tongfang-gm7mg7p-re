using System;
using System.CodeDom.Compiler;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Management;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Forms;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Threading;
using GCUService.WindowsW;
using Microsoft.Win32;
using Utility;

namespace DynamicDesk;

public class WindowW : Window, IComponentConnector
{
	private enum TaskBarLocation
	{
		TOP,
		BOTTOM,
		LEFT,
		RIGHT
	}

	private WindowsW_Viewmodel ViewModel = WindowsW_Viewmodel.Instance;

	private string _MonitorLocation;

	private bool _BackgroundShow;

	private string _BackgroundPlayType;

	private bool _Monitorshow;

	private string _VideoFileName;

	private string _MonitorColor;

	private double taskvarWidth = 40.0;

	private string _MonitorTransparent;

	private string _MonitorSize;

	private string _MonitorVideoList;

	private bool _MonitorHotkey;

	private List<string> VedioList = new List<string>();

	private object WindowWLock = new object();

	private static readonly WindowW model = new WindowW();

	private List<BoxItem> BoxsList = new List<BoxItem>();

	public EventHandler HotKeyEventHandler;

	private bool Fnkey;

	private ManagementEventWatcher watcher;

	private bool diving = true;

	private float Scaling;

	private IntPtr programIntPtr = IntPtr.Zero;

	private DispatcherTimer timer = new DispatcherTimer();

	private string CurrentFileName;

	internal WindowW DivingWindow;

	internal Grid WindowMainGrid;

	internal MediaElement mediaElement;

	internal StackPanel mainPanel;

	internal BoxItem CPUBoxItem;

	internal BoxItem GPUBoxItem;

	internal BoxItem MemoryBoxItem;

	internal BoxItem BatteryBoxItem;

	private bool _contentLoaded;

	public string MonitorLocation
	{
		get
		{
			_MonitorLocation = Convert.ToString(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorLocation", MONITORLOCATION.BOTTOM.ToString(), RegistryValueKind.String));
			return _MonitorLocation;
		}
		set
		{
			if (value != _MonitorLocation)
			{
				_MonitorLocation = value;
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorLocation", _MonitorLocation, RegistryValueKind.String);
			}
		}
	}

	public string VideoFileName
	{
		get
		{
			_VideoFileName = Convert.ToString(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "VideoFileName", LogCtrl.GetParentDirectoryPath(System.Windows.Forms.Application.StartupPath, 2) + "\\logo\\default.mp4", RegistryValueKind.String));
			return _VideoFileName;
		}
		set
		{
			if (value != _VideoFileName)
			{
				_VideoFileName = value;
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "VideoFileName", _VideoFileName, RegistryValueKind.String);
			}
		}
	}

	public bool BackgroundShow
	{
		get
		{
			_BackgroundShow = Convert.ToBoolean(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "BackgroundShow", false, RegistryValueKind.DWord));
			return _BackgroundShow;
		}
		set
		{
			if (value != _BackgroundShow)
			{
				_BackgroundShow = value;
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "BackgroundShow", _BackgroundShow, RegistryValueKind.DWord);
			}
		}
	}

	public string BackgroundPlayType
	{
		get
		{
			_BackgroundPlayType = Convert.ToString(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "BackgroundPlayType", "Single", RegistryValueKind.String));
			return _BackgroundPlayType;
		}
		set
		{
			if (value != _BackgroundPlayType)
			{
				_BackgroundPlayType = value;
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "BackgroundPlayType", _BackgroundPlayType, RegistryValueKind.String);
			}
		}
	}

	public bool Monitorshow
	{
		get
		{
			_Monitorshow = Convert.ToBoolean(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "Monitorshow", false, RegistryValueKind.DWord));
			return _Monitorshow;
		}
		set
		{
			if (value != _Monitorshow)
			{
				_Monitorshow = value;
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "Monitorshow", _Monitorshow, RegistryValueKind.DWord);
			}
		}
	}

	public string MonitorColor
	{
		get
		{
			_MonitorColor = Convert.ToString(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorColor", "#FFFFFFFF", RegistryValueKind.String));
			return _MonitorColor;
		}
		set
		{
			if (value != _MonitorColor)
			{
				_MonitorColor = value;
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorColor", _MonitorColor, RegistryValueKind.String);
			}
		}
	}

	public string MonitorSize
	{
		get
		{
			_MonitorSize = Convert.ToString(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorSize", "1", RegistryValueKind.String));
			return _MonitorSize;
		}
		set
		{
			if (value != _MonitorSize)
			{
				_MonitorSize = value;
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorSize", _MonitorSize, RegistryValueKind.String);
			}
		}
	}

	public string MonitorTransparent
	{
		get
		{
			_MonitorTransparent = Convert.ToString(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorTransparent", "0.6", RegistryValueKind.String));
			return _MonitorTransparent;
		}
		set
		{
			if (value != _MonitorTransparent)
			{
				_MonitorTransparent = value;
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorTransparent", _MonitorTransparent, RegistryValueKind.String);
			}
		}
	}

	public string MonitorVideoList
	{
		get
		{
			_MonitorVideoList = Convert.ToString(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorVideoList", "", RegistryValueKind.String));
			return _MonitorVideoList;
		}
		set
		{
			if (value != _MonitorVideoList)
			{
				_MonitorVideoList = value;
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorVideoList", _MonitorVideoList.ToString(), RegistryValueKind.String);
			}
		}
	}

	public bool MonitorHotkey
	{
		get
		{
			_MonitorHotkey = Convert.ToBoolean(RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorHotkey", false, RegistryValueKind.DWord));
			return _MonitorHotkey;
		}
		set
		{
			if (value != _MonitorHotkey)
			{
				_MonitorHotkey = value;
				RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\Monitor", "MonitorHotkey", _MonitorHotkey, RegistryValueKind.DWord);
			}
		}
	}

	public static WindowW Instance => model;

	private TaskBarLocation GetTaskBarLocation()
	{
		TaskBarLocation result = TaskBarLocation.BOTTOM;
		if (Screen.PrimaryScreen.WorkingArea.Width == Screen.PrimaryScreen.Bounds.Width)
		{
			if (Screen.PrimaryScreen.WorkingArea.Top > 0)
			{
				result = TaskBarLocation.TOP;
			}
			taskvarWidth = Screen.PrimaryScreen.Bounds.Height - Screen.PrimaryScreen.WorkingArea.Height;
		}
		else
		{
			result = ((Screen.PrimaryScreen.WorkingArea.Left <= 0) ? TaskBarLocation.RIGHT : TaskBarLocation.LEFT);
			taskvarWidth = Screen.PrimaryScreen.Bounds.Width - Screen.PrimaryScreen.WorkingArea.Width;
		}
		return result;
	}

	private WindowW()
	{
		InitializeComponent();
		MemoryBoxItem.TempatureGrid.Visibility = Visibility.Collapsed;
		BatteryBoxItem.TempatureGrid.Visibility = Visibility.Collapsed;
		InitalizeColor(GPUBoxItem, "#00BBFF", "#EE7700");
		InitalizeColor(CPUBoxItem, "#00BBFF", "#EE7700");
		InitalizeColor(MemoryBoxItem, "#00BBFF", "#EE7700");
		InitalizeColor(BatteryBoxItem, "#EE7700", "#99DD00");
		base.DataContext = ViewModel;
		ViewModel.dispatcher = base.Dispatcher;
		_ = SystemParameters.WorkArea.Width;
		_ = SystemParameters.WorkArea.Height;
		_ = SystemParameters.FullPrimaryScreenWidth;
		_ = SystemParameters.FullPrimaryScreenHeight;
		base.WindowState = WindowState.Maximized;
		ScreenChanged();
		base.SizeChanged += Window1_SizeChanged;
		base.StateChanged += Window1_StateChanged;
		base.ContentRendered += Window1_ContentRendered;
		base.IsVisibleChanged += Window1_IsVisibleChanged;
		base.Deactivated += Window1_Deactivated;
		base.Activated += Window1_Activated;
		base.MouseMove += Window1_MouseMove;
		SystemEvents.DisplaySettingsChanged += SystemEvents_DisplaySettingsChanged;
		StartWMIReceiveEvent(WMIHandleEvent);
	}

	private void SystemEvents_DisplaySettingsChanged(object sender, EventArgs e)
	{
		Screen.AllScreens.First().GetDpi(DpiType.Effective, out var dpiX, out var _);
		float scaling = Convert.ToSingle((float)dpiX / 96f);
		Scaling = scaling;
		int width = Screen.AllScreens.First().Bounds.Width;
		int height = Screen.AllScreens.First().Bounds.Height;
		base.Left = 0.0;
		WindowMainGrid.Width = Convert.ToDouble((float)width / Scaling);
		WindowMainGrid.Height = Convert.ToDouble((float)height / Scaling);
	}

	public void SetHotkeyEnable(bool ONOFF)
	{
		MonitorHotkey = ONOFF;
		_ = MonitorHotkey;
	}

	private void HookManager_KeyUp(object sender, System.Windows.Forms.KeyEventArgs e)
	{
		if (Convert.ToInt32(e.KeyData) == Convert.ToInt32(Keys.F16 | Keys.F17))
		{
			Fnkey = false;
		}
	}

	private void HookManager_KeyDown(object sender, System.Windows.Forms.KeyEventArgs e)
	{
		if (Convert.ToInt32(e.KeyData) == Convert.ToInt32(Keys.F16 | Keys.F17))
		{
			Fnkey = true;
		}
		if (Fnkey && e.KeyCode == Keys.P)
		{
			if (MonitorLocation == MONITORLOCATION.RIGHT.ToString())
			{
				ShowMonitorLocation(MONITORLOCATION.BOTTOM.ToString());
			}
			else if (MonitorLocation == MONITORLOCATION.BOTTOM.ToString())
			{
				ShowMonitorLocation(MONITORLOCATION.LEFT.ToString());
			}
			else if (MonitorLocation == MONITORLOCATION.LEFT.ToString())
			{
				ShowMonitorLocation(MONITORLOCATION.TOP.ToString());
			}
			else if (MonitorLocation == MONITORLOCATION.TOP.ToString())
			{
				ShowMonitorLocation(MONITORLOCATION.RIGHT.ToString());
			}
			if (HotKeyEventHandler != null)
			{
				HotKeyEventHandler(MonitorLocation, null);
			}
		}
	}

	private void WMIHandleEvent(object sender, EventArrivedEventArgs e)
	{
		Console.WriteLine("Recive scancode " + Convert.ToInt32(e.NewEvent.SystemProperties["ULong"].Value.ToString()));
	}

	public void StartWMIReceiveEvent(EventArrivedEventHandler WMIHandleEvent)
	{
		try
		{
			WqlEventQuery query = new WqlEventQuery("SELECT * FROM AcpiTest_EventULong");
			watcher = new ManagementEventWatcher(new ManagementScope("\\\\.\\Root\\WMI"), query);
			watcher.EventArrived += WMIHandleEvent;
			watcher.Start();
		}
		catch (ManagementException ex)
		{
			Console.WriteLine("An error occurred while trying to receive an event: " + ex.Message);
		}
	}

	internal void SetVideoList(List<string> setVideoList)
	{
		VedioList = setVideoList;
		MonitorVideoList = Json.Stringify(VedioList);
	}

	private void InitalizeColor(BoxItem BoxItem, string firstColor, string lastColor)
	{
		System.Drawing.Color color = ColorTranslator.FromHtml(firstColor);
		System.Drawing.Color color2 = ColorTranslator.FromHtml(lastColor);
		BoxItem.ItemPercentColorF.Color = System.Windows.Media.Color.FromArgb(color.A, color.R, color.G, color.B);
		BoxItem.ItemPercentColorL.Color = System.Windows.Media.Color.FromArgb(color2.A, color2.R, color2.G, color2.B);
		BoxItem.ItemTempatureColorF.Color = System.Windows.Media.Color.FromArgb(color.A, color.R, color.G, color.B);
		BoxItem.ItemTempatureColorL.Color = System.Windows.Media.Color.FromArgb(color2.A, color2.R, color2.G, color2.B);
		BoxsList.Add(BoxItem);
	}

	public void SetColor(string StartcolorHex, string EndcolorHex)
	{
		MonitorColor = StartcolorHex;
		System.Drawing.Color NewStartColor = ColorTranslator.FromHtml(MonitorColor);
		System.Drawing.Color NewEndColor = ColorTranslator.FromHtml(MonitorColor);
		float colorChange = 0f;
		foreach (BoxItem item in BoxsList)
		{
			base.Dispatcher.BeginInvoke((Action)delegate
			{
				GradientStopCollection gsc = new GradientStopCollection(2)
				{
					new GradientStop(System.Windows.Media.Color.FromArgb(NewStartColor.A, NewStartColor.R, NewStartColor.G, NewStartColor.B), 0.0),
					new GradientStop(System.Windows.Media.Color.FromArgb(NewEndColor.A, NewEndColor.R, NewEndColor.G, NewEndColor.B), 1.0)
				};
				System.Windows.Media.Brush brush = new SolidColorBrush(System.Windows.Media.Color.FromArgb(byte.MaxValue, Convert.ToByte(NewStartColor.R ^ 0xFF), Convert.ToByte(NewStartColor.G ^ 0xFF), Convert.ToByte(NewStartColor.B ^ 0xFF)));
				System.Windows.Media.Color relativeColor = gsc.GetRelativeColor(colorChange);
				item.ItemTitleBackgrond.Fill = new SolidColorBrush(relativeColor);
				item.ShowBackGround.Fill = new SolidColorBrush(relativeColor);
				item.SplitLine.Fill = brush;
				item.SplitLine.Stroke = brush;
				item.ItemNameText.Foreground = brush;
				item.ItemPercentValueText.Foreground = brush;
				item.ItemPercentValueTextDegreeText.Foreground = brush;
				item.ItemTempatureValueText.Foreground = brush;
				item.ItemTempatureValueDegreeText.Foreground = brush;
			}, DispatcherPriority.Background);
		}
	}

	public void SetTransparent(string percent)
	{
		MonitorTransparent = percent;
		try
		{
			float num = Convert.ToSingle(percent);
			foreach (BoxItem boxs in BoxsList)
			{
				boxs.ShowBackGround.Opacity = num;
			}
		}
		catch (Exception)
		{
			mainPanel.Opacity = 1.0;
		}
	}

	public void SetSize(string sizepercent)
	{
		MonitorSize = sizepercent;
		try
		{
			float num = Convert.ToSingle(MonitorSize);
			foreach (BoxItem boxs in BoxsList)
			{
				boxs.sizeScale.ScaleX = num;
				boxs.sizeScale.ScaleY = num;
				FixLoaction(boxs, num);
			}
		}
		catch (Exception)
		{
			mainPanel.Opacity = 1.0;
		}
	}

	private void FixLoaction(BoxItem item, float p)
	{
		double num = 0.0;
		if (p == 1.2f)
		{
			num = 10.0;
		}
		if (p == 0.8f)
		{
			num = -30.0;
		}
		double num2 = 10.0 * Math.Pow(p, 5.0);
		if (MonitorLocation == MONITORLOCATION.RIGHT.ToString())
		{
			item.Margin = new Thickness(num2, num2, num2 + num, num2);
		}
		else
		{
			item.Margin = new Thickness(num2, num2, num2, num2);
		}
	}

	[DllImport("gdi32.dll")]
	private static extern int GetDeviceCaps(IntPtr hdc, int Index);

	private IEnumerable<string> Display(DpiType type)
	{
		Screen[] allScreens = Screen.AllScreens;
		foreach (Screen screen in allScreens)
		{
			screen.GetDpi(type, out var dpiX, out var dpiY);
			yield return screen.DeviceName + " - dpiX=" + dpiX + ", dpiY=" + dpiY;
		}
	}

	public static double MillimetersToPixelsWidth(double length)
	{
		Graphics graphics = Graphics.FromHwnd(new System.Windows.Forms.Panel().Handle);
		IntPtr hdc = graphics.GetHdc();
		int deviceCaps = GetDeviceCaps(hdc, 4);
		int deviceCaps2 = GetDeviceCaps(hdc, 8);
		graphics.ReleaseHdc(hdc);
		return (double)deviceCaps2 / (double)deviceCaps * length;
	}

	private void ScreenChanged()
	{
		if (diving)
		{
			diving = false;
			Screen.AllScreens.First().GetDpi(DpiType.Effective, out var dpiX, out var _);
			float scaling = Convert.ToSingle((float)dpiX / 96f);
			Scaling = scaling;
			int width = Screen.AllScreens.First().Bounds.Width;
			int height = Screen.AllScreens.First().Bounds.Height;
			base.Left = 0.0;
			WindowMainGrid.Width = Convert.ToDouble((float)width / Scaling);
			WindowMainGrid.Height = Convert.ToDouble((float)height / Scaling);
			Thread.Sleep(100);
			buildDivingWindows();
			diving = true;
		}
	}

	private void SetChart()
	{
	}

	public void ShowMainGrid(bool ONOFF)
	{
		if (ONOFF)
		{
			WindowMainGrid.Visibility = Visibility.Visible;
		}
		else
		{
			WindowMainGrid.Visibility = Visibility.Hidden;
		}
	}

	public void ShowBackground(bool ONOFF)
	{
		if (ONOFF)
		{
			BackgroundShow = true;
			mediaElement.Visibility = Visibility.Visible;
			ChangeAndPlayVideo(VideoFileName);
		}
		else
		{
			BackgroundShow = false;
			mediaElement.Visibility = Visibility.Hidden;
			mediaElement.Stop();
		}
		CheckItself();
	}

	public void ShowMonitor(bool ONOFF)
	{
		if (ONOFF)
		{
			Monitorshow = true;
			mainPanel.Visibility = Visibility.Visible;
		}
		else
		{
			Monitorshow = false;
			mainPanel.Visibility = Visibility.Hidden;
		}
		CheckItself();
	}

	private void CheckItself()
	{
		if (!BackgroundShow && !Monitorshow)
		{
			return;
		}
		lock (WindowWLock)
		{
			if (base.Visibility == Visibility.Hidden)
			{
				Show();
				Console.WriteLine("WindowW Show");
			}
		}
	}

	public void ShowMonitorLocation(string location)
	{
		MonitorLocation = location;
		if (location == MONITORLOCATION.RRGIHTTOP.ToString())
		{
			ShowRightTop();
		}
		else if (location == MONITORLOCATION.RIGHTBOTTOM.ToString())
		{
			ShowRightBottom();
		}
		else if (location == MONITORLOCATION.LEFTTOP.ToString())
		{
			ShowLeftTop();
		}
		else if (location == MONITORLOCATION.LEFTBOTTOM.ToString())
		{
			ShowLeftBottom();
		}
		else if (location == MONITORLOCATION.RIGHT.ToString())
		{
			ShowRightCenter();
		}
		else if (location == MONITORLOCATION.LEFT.ToString())
		{
			ShowLeftCenter();
		}
		else if (location == MONITORLOCATION.TOP.ToString())
		{
			ShowCenterTop();
		}
		else if (location == MONITORLOCATION.BOTTOM.ToString())
		{
			ShowCenterBottom();
		}
		float p = Convert.ToSingle(MonitorSize);
		foreach (BoxItem boxs in BoxsList)
		{
			FixLoaction(boxs, p);
		}
	}

	public void ShowRightTop()
	{
		mainPanel.HorizontalAlignment = System.Windows.HorizontalAlignment.Right;
		mainPanel.VerticalAlignment = VerticalAlignment.Top;
	}

	public void ShowRightBottom()
	{
		mainPanel.HorizontalAlignment = System.Windows.HorizontalAlignment.Right;
		mainPanel.VerticalAlignment = VerticalAlignment.Bottom;
	}

	public void ShowRightCenter()
	{
		mainPanel.Orientation = System.Windows.Controls.Orientation.Vertical;
		if (GetTaskBarLocation() == TaskBarLocation.RIGHT)
		{
			mainPanel.Margin = new Thickness(0.0, 0.0, taskvarWidth, 0.0);
		}
		mainPanel.HorizontalAlignment = System.Windows.HorizontalAlignment.Right;
		mainPanel.VerticalAlignment = VerticalAlignment.Center;
	}

	public void ShowLeftTop()
	{
		mainPanel.HorizontalAlignment = System.Windows.HorizontalAlignment.Left;
		mainPanel.VerticalAlignment = VerticalAlignment.Top;
	}

	public void ShowLeftBottom()
	{
		mainPanel.HorizontalAlignment = System.Windows.HorizontalAlignment.Left;
		mainPanel.VerticalAlignment = VerticalAlignment.Bottom;
	}

	public void ShowLeftCenter()
	{
		mainPanel.Orientation = System.Windows.Controls.Orientation.Vertical;
		if (GetTaskBarLocation() == TaskBarLocation.LEFT)
		{
			mainPanel.Margin = new Thickness(taskvarWidth, 0.0, 0.0, 0.0);
		}
		mainPanel.HorizontalAlignment = System.Windows.HorizontalAlignment.Left;
		mainPanel.VerticalAlignment = VerticalAlignment.Center;
	}

	public void ShowCenterTop()
	{
		mainPanel.Orientation = System.Windows.Controls.Orientation.Horizontal;
		if (GetTaskBarLocation() == TaskBarLocation.TOP)
		{
			mainPanel.Margin = new Thickness(0.0, taskvarWidth, 0.0, 0.0);
		}
		mainPanel.HorizontalAlignment = System.Windows.HorizontalAlignment.Center;
		mainPanel.VerticalAlignment = VerticalAlignment.Top;
	}

	public void ShowCenterBottom()
	{
		mainPanel.Orientation = System.Windows.Controls.Orientation.Horizontal;
		if (GetTaskBarLocation() == TaskBarLocation.BOTTOM)
		{
			mainPanel.Margin = new Thickness(0.0, 0.0, 0.0, taskvarWidth);
		}
		mainPanel.HorizontalAlignment = System.Windows.HorizontalAlignment.Center;
		mainPanel.VerticalAlignment = VerticalAlignment.Bottom;
	}

	public void ShowCenterCenter()
	{
		mainPanel.HorizontalAlignment = System.Windows.HorizontalAlignment.Center;
		mainPanel.VerticalAlignment = VerticalAlignment.Center;
	}

	private void Window1_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
	{
		ScreenChanged();
	}

	private void Window1_Activated(object sender, EventArgs e)
	{
		ScreenChanged();
	}

	private void Window1_Deactivated(object sender, EventArgs e)
	{
		ScreenChanged();
	}

	private void Window1_IsVisibleChanged(object sender, DependencyPropertyChangedEventArgs e)
	{
		ScreenChanged();
	}

	private void Window1_ContentRendered(object sender, EventArgs e)
	{
		ScreenChanged();
	}

	private void Window1_StateChanged(object sender, EventArgs e)
	{
		ScreenChanged();
	}

	private void Window1_SizeChanged(object sender, SizeChangedEventArgs e)
	{
		ScreenChanged();
	}

	public void Init()
	{
		programIntPtr = Win32.FindWindow("Progman", null);
		if (!(programIntPtr != IntPtr.Zero))
		{
			return;
		}
		IntPtr zero = IntPtr.Zero;
		Win32.SendMessageTimeout(programIntPtr, 1324u, IntPtr.Zero, IntPtr.Zero, 0u, 1000u, zero);
		Win32.EnumWindows(delegate(IntPtr hwnd, IntPtr lParam)
		{
			if (Win32.FindWindowEx(hwnd, IntPtr.Zero, "SHELLDLL_DefView", null) != IntPtr.Zero)
			{
				Win32.ShowWindow(Win32.FindWindowEx(IntPtr.Zero, hwnd, "WorkerW", null), 0);
			}
			return true;
		}, IntPtr.Zero);
	}

	private void buildDivingWindows()
	{
		try
		{
			IntPtr hwnd = new WindowInteropHelper(this).EnsureHandle();
			Init();
			Win32.SetParent(hwnd, programIntPtr);
		}
		catch (Exception)
		{
		}
	}

	private void Window_Closed(object sender, EventArgs e)
	{
	}

	private void mediaElement_Loaded(object sender, RoutedEventArgs e)
	{
		ChangeAndPlayVideo(VideoFileName);
	}

	public void ChangeAndPlayVideo(string file)
	{
		VideoFileName = file;
		if (File.Exists(file) && BackgroundShow)
		{
			CurrentFileName = VideoFileName;
			mediaElement.LoadedBehavior = MediaState.Manual;
			mediaElement.Source = new Uri(VideoFileName, UriKind.Absolute);
			mediaElement.Volume = 0.0;
			mediaElement.MediaEnded -= MediaElement_MediaEnded;
			mediaElement.MediaEnded += MediaElement_MediaEnded;
			mediaElement.Stop();
			Thread.Sleep(100);
			mediaElement.Play();
		}
	}

	private void MediaElement_MediaEnded(object sender, RoutedEventArgs e)
	{
		try
		{
			if (BackgroundPlayType == "Slider")
			{
				int num = VedioList.IndexOf(CurrentFileName);
				num = ((num != VedioList.Count - 1) ? (num + 1) : 0);
				ChangeAndPlayVideo(VedioList[num]);
			}
			else if (BackgroundPlayType == "Random")
			{
				int index = new Random().Next(0, VedioList.Count - 1);
				ChangeAndPlayVideo(VedioList[index]);
			}
			else
			{
				mediaElement.Stop();
				mediaElement.Play();
			}
		}
		catch (Exception)
		{
			mediaElement.Stop();
			mediaElement.Play();
		}
	}

	private void Window_Loaded_1(object sender, RoutedEventArgs e)
	{
		try
		{
			(PresentationSource.FromVisual(this) as HwndSource).CompositionTarget.RenderMode = RenderMode.Default;
		}
		catch (Exception)
		{
		}
	}

	private void Window_Closed_1(object sender, EventArgs e)
	{
	}

	public void SetBackgroundPlayType(string playType)
	{
		BackgroundPlayType = playType;
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
	public void InitializeComponent()
	{
		if (!_contentLoaded)
		{
			_contentLoaded = true;
			Uri resourceLocator = new Uri("/GCUService;component/windowsw/windoww.xaml", UriKind.Relative);
			System.Windows.Application.LoadComponent(this, resourceLocator);
		}
	}

	void IComponentConnector.InitializeComponent()
	{
		//ILSpy generated this explicit interface implementation from .override directive in InitializeComponent
		this.InitializeComponent();
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
	internal Delegate _CreateDelegate(Type delegateType, string handler)
	{
		return Delegate.CreateDelegate(delegateType, this, handler);
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
	[EditorBrowsable(EditorBrowsableState.Never)]
	void IComponentConnector.Connect(int connectionId, object target)
	{
		switch (connectionId)
		{
		case 1:
			DivingWindow = (WindowW)target;
			DivingWindow.Loaded += Window_Loaded_1;
			DivingWindow.Closed += Window_Closed;
			break;
		case 2:
			WindowMainGrid = (Grid)target;
			break;
		case 3:
			mediaElement = (MediaElement)target;
			mediaElement.Loaded += mediaElement_Loaded;
			break;
		case 4:
			mainPanel = (StackPanel)target;
			break;
		case 5:
			CPUBoxItem = (BoxItem)target;
			break;
		case 6:
			GPUBoxItem = (BoxItem)target;
			break;
		case 7:
			MemoryBoxItem = (BoxItem)target;
			break;
		case 8:
			BatteryBoxItem = (BoxItem)target;
			break;
		default:
			_contentLoaded = true;
			break;
		}
	}
}
