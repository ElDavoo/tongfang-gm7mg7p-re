using System;
using System.CodeDom.Compiler;
using System.ComponentModel;
using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Shapes;

namespace DynamicDesk;

public class BoxItem : UserControl, IComponentConnector
{
	public static readonly DependencyProperty ItemNameProperty = DependencyProperty.Register("ItemName", typeof(string), typeof(BoxItem), new PropertyMetadata("", OnItemNamePropertyChanged));

	public static readonly DependencyProperty PercentProperty = DependencyProperty.Register("Percent", typeof(double), typeof(BoxItem), new PropertyMetadata(0.0, OnItemPercentPropertyChanged));

	public static readonly DependencyProperty PercentTextProperty = DependencyProperty.Register("PercentText", typeof(string), typeof(BoxItem), new PropertyMetadata("", OnItemPercentTextPropertyChanged));

	public static readonly DependencyProperty TempatureProperty = DependencyProperty.Register("Tempature", typeof(double), typeof(BoxItem), new PropertyMetadata(0.0, OnItemTempaturePropertyChanged));

	public static readonly DependencyProperty TempatureTextProperty = DependencyProperty.Register("TempatureText", typeof(string), typeof(BoxItem), new PropertyMetadata("", OnItemTempatureTextPropertyChanged));

	internal Grid MonitorMainGrid;

	internal ScaleTransform sizeScale;

	internal Rectangle SplitLine;

	internal Rectangle ItemTitleBackgrond;

	internal TextBlock ItemNameText;

	internal Rectangle ShowBackGround;

	internal GradientStop ItemPercentColorF;

	internal GradientStop ItemPercentColorL;

	internal Rectangle ItemPercentValue;

	internal TextBlock ItemPercentValueText;

	internal TextBlock ItemPercentValueTextDegreeText;

	internal Grid TempatureGrid;

	internal GradientStop ItemTempatureColorF;

	internal GradientStop ItemTempatureColorL;

	internal Rectangle ItemTempatureValue;

	internal TextBlock ItemTempatureValueText;

	internal TextBlock ItemTempatureValueDegreeText;

	private bool _contentLoaded;

	public string ItemName
	{
		get
		{
			return (string)GetValue(ItemNameProperty);
		}
		set
		{
			SetValue(ItemNameProperty, value);
		}
	}

	public double Percent
	{
		get
		{
			return (double)GetValue(PercentProperty);
		}
		set
		{
			SetValue(PercentProperty, value);
		}
	}

	public string PercentText
	{
		get
		{
			return (string)GetValue(PercentTextProperty);
		}
		set
		{
			SetValue(PercentTextProperty, value);
		}
	}

	public double Tempature
	{
		get
		{
			return (double)GetValue(TempatureProperty);
		}
		set
		{
			SetValue(TempatureProperty, value);
		}
	}

	public string TempatureText
	{
		get
		{
			return (string)GetValue(TempatureTextProperty);
		}
		set
		{
			SetValue(TempatureTextProperty, value);
		}
	}

	private static void OnItemTempaturePropertyChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
	{
		if (d is BoxItem boxItem)
		{
			if (boxItem == null)
			{
				throw new ArgumentOutOfRangeException("Value", "ItemBox Precent");
			}
			boxItem.ItemTempatureValue.Width = 100.0 - Convert.ToDouble(e.NewValue);
		}
	}

	private static void OnItemTempatureTextPropertyChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
	{
		if (d is BoxItem boxItem)
		{
			if (boxItem == null)
			{
				throw new ArgumentOutOfRangeException("Value", "ItemBox Precent");
			}
			boxItem.ItemTempatureValueText.Text = Convert.ToString(e.NewValue);
		}
	}

	public BoxItem()
	{
		InitializeComponent();
	}

	private static void OnItemNamePropertyChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
	{
		if (d is BoxItem boxItem)
		{
			if (boxItem == null)
			{
				throw new ArgumentOutOfRangeException("Name", "ItemBox Name");
			}
			boxItem.ItemNameText.Text = Convert.ToString(e.NewValue);
		}
	}

	private static void OnItemPercentPropertyChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
	{
		if (d is BoxItem boxItem)
		{
			if (boxItem == null)
			{
				throw new ArgumentOutOfRangeException("Value", "ItemBox Precent");
			}
			double num = 100.0 - Convert.ToDouble(e.NewValue);
			if (num < 0.0)
			{
				num = 0.0;
			}
			boxItem.ItemPercentValue.Width = num;
		}
	}

	private static void OnItemPercentTextPropertyChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
	{
		if (d is BoxItem boxItem)
		{
			if (boxItem == null)
			{
				throw new ArgumentOutOfRangeException("Value", "ItemBox Precent");
			}
			boxItem.ItemPercentValueText.Text = Convert.ToString(e.NewValue);
		}
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
	public void InitializeComponent()
	{
		if (!_contentLoaded)
		{
			_contentLoaded = true;
			Uri resourceLocator = new Uri("/GCUService;component/windowsw/boxitem.xaml", UriKind.Relative);
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
			MonitorMainGrid = (Grid)target;
			break;
		case 2:
			sizeScale = (ScaleTransform)target;
			break;
		case 3:
			SplitLine = (Rectangle)target;
			break;
		case 4:
			ItemTitleBackgrond = (Rectangle)target;
			break;
		case 5:
			ItemNameText = (TextBlock)target;
			break;
		case 6:
			ShowBackGround = (Rectangle)target;
			break;
		case 7:
			ItemPercentColorF = (GradientStop)target;
			break;
		case 8:
			ItemPercentColorL = (GradientStop)target;
			break;
		case 9:
			ItemPercentValue = (Rectangle)target;
			break;
		case 10:
			ItemPercentValueText = (TextBlock)target;
			break;
		case 11:
			ItemPercentValueTextDegreeText = (TextBlock)target;
			break;
		case 12:
			TempatureGrid = (Grid)target;
			break;
		case 13:
			ItemTempatureColorF = (GradientStop)target;
			break;
		case 14:
			ItemTempatureColorL = (GradientStop)target;
			break;
		case 15:
			ItemTempatureValue = (Rectangle)target;
			break;
		case 16:
			ItemTempatureValueText = (TextBlock)target;
			break;
		case 17:
			ItemTempatureValueDegreeText = (TextBlock)target;
			break;
		default:
			_contentLoaded = true;
			break;
		}
	}
}
