using System;
using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;
using Utility;

namespace GCUService.MySystem;

internal class NotificationPanel : ContentControl
{
	private Image backgroundimg = new Image();

	private Button navigationBtn;

	private string m_GCU_EXE = "GamingCenterU.exe";

	private string m_sGCU = "GamingCenterU";

	private int ui_height = 150;

	private int ui_width = 250;

	public NotificationPanel(string titleString, string messageString)
	{
		base.Height = ui_height;
		base.Width = ui_width;
		Brush brush = new SolidColorBrush(Color.FromArgb(byte.MaxValue, byte.MaxValue, byte.MaxValue, byte.MaxValue));
		Brush background = new SolidColorBrush(Color.FromArgb(0, 0, 0, 0));
		Brush fill = new SolidColorBrush(Color.FromArgb(byte.MaxValue, 0, 0, 0));
		TextBlock element = new TextBlock
		{
			HorizontalAlignment = HorizontalAlignment.Left,
			Background = background,
			FontSize = 20.0,
			Margin = new Thickness(20.0, 15.0, 0.0, 0.0),
			Foreground = brush,
			Text = titleString
		};
		TextBlock element2 = new TextBlock
		{
			Background = background,
			HorizontalAlignment = HorizontalAlignment.Center,
			FontSize = 30.0,
			Margin = new Thickness(0.0, 0.0, 0.0, 0.0),
			Text = messageString,
			Foreground = brush
		};
		navigationBtn = new Button();
		navigationBtn.Width = 100.0;
		navigationBtn.BorderBrush = brush;
		navigationBtn.Background = background;
		navigationBtn.Foreground = brush;
		navigationBtn.Margin = new Thickness(0.0, 30.0, 0.0, 0.0);
		navigationBtn.Content = "Go to";
		navigationBtn.Click += NavigationBtn_Click;
		backgroundimg.Source = LoadBitmapFromResource("div-info-frame.png");
		backgroundimg.Stretch = Stretch.Fill;
		Rectangle element3 = new Rectangle
		{
			Fill = fill
		};
		Grid grid = new Grid
		{
			Margin = new Thickness(-55.0, -5.0, -55.0, -5.0)
		};
		StackPanel element4 = new StackPanel
		{
			HorizontalAlignment = HorizontalAlignment.Stretch,
			Children = 
			{
				(UIElement)element,
				(UIElement)element2,
				(UIElement)navigationBtn
			}
		};
		grid.Children.Add(element3);
		grid.Children.Add(backgroundimg);
		grid.Children.Add(element4);
		AddChild(grid);
	}

	private void NavigationBtn_Click(object sender, RoutedEventArgs e)
	{
		LogCtrl.Write("notifyIcon_DoubleClick");
		try
		{
			string text = LogCtrl.GetParentDirectoryPath(new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName, 2) + "\\Core";
			LogCtrl.Write($"BaseDirectoryPath = {text}");
			if (text != "")
			{
				CreateProcessAsUserWrapper.LaunchChildProcess(text + "\\" + m_GCU_EXE);
			}
			else
			{
				LogCtrl.Write("AP is not find.");
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("notifyIcon_DoubleClick Exception: " + ex.Message);
		}
	}

	public static BitmapImage LoadBitmapFromResource(string pathInApplication, Assembly assembly = null)
	{
		if (assembly == null)
		{
			assembly = Assembly.GetCallingAssembly();
		}
		if (pathInApplication[0] == '/')
		{
			pathInApplication = pathInApplication.Substring(1);
		}
		BitmapImage result = null;
		try
		{
			string text = "Assets/" + pathInApplication;
			result = new BitmapImage(new Uri("pack://application:,,,/" + assembly.GetName().Name + ";component/" + text, UriKind.Absolute));
		}
		catch (Exception)
		{
		}
		return result;
	}
}
