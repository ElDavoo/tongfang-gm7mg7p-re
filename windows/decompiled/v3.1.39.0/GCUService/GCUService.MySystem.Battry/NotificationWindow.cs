using System;
using System.CodeDom.Compiler;
using System.ComponentModel;
using System.Diagnostics;
using System.Media;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Markup;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;

namespace GCUService.MySystem.Battry;

public class NotificationWindow : Window, IComponentConnector
{
	public EventHandler LoadCompleted;

	private int NotifyTimeSpan = 1000;

	internal Image CloseFrom;

	internal new TextBlock Title;

	internal TextBlock Message;

	internal Image StepImage;

	internal TextBlock stepString;

	internal TextBlock stepInfo;

	private bool _contentLoaded;

	public double TopFrom { get; set; }

	public NotificationWindow(string titleString, string messageString, string stepString, string stepInfoString, string imgstring)
	{
		InitializeComponent();
		Title.Text = titleString;
		Message.Text = messageString;
		this.stepString.Text = stepString;
		if (imgstring != null)
		{
			StepImage.Source = new BitmapImage(new Uri(imgstring));
		}
		else
		{
			StepImage.Source = null;
		}
		stepInfo.Text = stepInfoString;
	}

	private void Button_Click(object sender, RoutedEventArgs e)
	{
	}

	private void NotificationWindow_Loaded(object sender, RoutedEventArgs e)
	{
	}

	private static void Invoke(Window win, Action a)
	{
		win.Dispatcher.Invoke(a);
	}

	private void Window_ContentRendered(object sender, EventArgs e)
	{
		NotificationWindow self = sender as NotificationWindow;
		if (self == null)
		{
			return;
		}
		self.UpdateLayout();
		SystemSounds.Asterisk.Play();
		double right = SystemParameters.WorkArea.Right;
		self.Top = self.TopFrom - self.ActualHeight;
		DoubleAnimation animation = new DoubleAnimation();
		animation.Duration = new Duration(TimeSpan.FromMilliseconds(NotifyTimeSpan));
		animation.From = right;
		animation.To = right - self.ActualWidth;
		self.BeginAnimation(Window.LeftProperty, animation);
		Task.Factory.StartNew(delegate
		{
			Thread.Sleep(TimeSpan.FromSeconds(10.0));
			Invoke(self, delegate
			{
				animation = new DoubleAnimation();
				animation.Duration = new Duration(TimeSpan.FromMilliseconds(NotifyTimeSpan));
				animation.Completed += delegate
				{
					self.Close();
				};
				animation.From = self.ActualHeight;
				animation.To = 0.0;
				self.BeginAnimation(FrameworkElement.HeightProperty, animation);
			});
		});
	}

	private void Window_Activated(object sender, EventArgs e)
	{
	}

	private void CloseFrom_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
	{
		_ = SystemParameters.WorkArea.Right;
		DoubleAnimation doubleAnimation = new DoubleAnimation();
		doubleAnimation.Duration = new Duration(TimeSpan.FromMilliseconds(NotifyTimeSpan));
		doubleAnimation.Completed += delegate
		{
			Close();
		};
		doubleAnimation.From = base.ActualHeight;
		doubleAnimation.To = 0.0;
		BeginAnimation(FrameworkElement.HeightProperty, doubleAnimation);
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
	public void InitializeComponent()
	{
		if (!_contentLoaded)
		{
			_contentLoaded = true;
			Uri resourceLocator = new Uri("/GCUService;component/mysystem/battry/notificationwindow.xaml", UriKind.Relative);
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
			((NotificationWindow)target).Loaded += NotificationWindow_Loaded;
			((NotificationWindow)target).ContentRendered += Window_ContentRendered;
			((NotificationWindow)target).Activated += Window_Activated;
			break;
		case 2:
			CloseFrom = (Image)target;
			CloseFrom.MouseLeftButtonDown += CloseFrom_MouseLeftButtonDown;
			break;
		case 3:
			Title = (TextBlock)target;
			break;
		case 4:
			Message = (TextBlock)target;
			break;
		case 5:
			StepImage = (Image)target;
			break;
		case 6:
			stepString = (TextBlock)target;
			break;
		case 7:
			stepInfo = (TextBlock)target;
			break;
		case 8:
			((Button)target).Click += Button_Click;
			break;
		default:
			_contentLoaded = true;
			break;
		}
	}
}
