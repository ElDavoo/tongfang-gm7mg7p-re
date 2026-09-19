using System;
using System.Collections.Generic;
using System.Windows;
using Colourful;
using Colourful.Conversion;
using Colourful.Implementation.RGB;

namespace GCUService.MySetting;

internal class ColorSpaceEffect
{
	private enum AdjustType
	{
		ColorSpace,
		Custom
	}

	private double[] ColorAdject = new double[3] { 128.0, 128.0, 128.0 };

	private double[] ColortempatueRGB = new double[3] { 90.0, 90.0, 90.0 };

	private Dictionary<string, double> RGBStandard = new Dictionary<string, double>();

	private double _gamma = 1.0;

	private double _brightness = 100.0;

	private int _kevlvin = 6500;

	private XYZColor _wp = Illuminants.D65;

	private RGBWorkingSpace _colorSpace = RGBWorkingSpaces.CIERGB;

	private Point[] CustomColorSpace = new Point[3];

	public void Default()
	{
		_gamma = 1.0;
		_brightness = 50.0;
		_wp = Illuminants.D65;
		_kevlvin = 6500;
		_colorSpace = RGBWorkingSpaces.CIERGB;
		SetColor(128.0, 128.0, 128.0);
		UpdateSetting(AdjustType.ColorSpace);
	}

	public void VibrantMode()
	{
		_wp = Illuminants.D65;
		_colorSpace = RGBWorkingSpaces.CIERGB;
		UpdateSetting(AdjustType.ColorSpace);
	}

	public void VideoMode()
	{
		_wp = Illuminants.D65;
		_colorSpace = RGBWorkingSpaces.CIERGB;
		CustomColorSpace[0] = new Point(0.68, 0.32);
		CustomColorSpace[1] = new Point(0.265, 0.69);
		CustomColorSpace[2] = new Point(0.15, 0.06);
		UpdateSetting(AdjustType.Custom);
	}

	public void InternetMode()
	{
		_wp = Illuminants.D65;
		_colorSpace = RGBWorkingSpaces.Rec709;
		UpdateSetting(AdjustType.ColorSpace);
	}

	public void LowBlueMode()
	{
		_wp = Illuminants.D65;
		_colorSpace = RGBWorkingSpaces.CIERGB;
		UpdateSetting(AdjustType.ColorSpace);
	}

	public void CinemaMode()
	{
		_wp = Illuminants.D50;
		_colorSpace = RGBWorkingSpaces.CIERGB;
		CustomColorSpace[0] = new Point(0.68, 0.32);
		CustomColorSpace[1] = new Point(0.265, 0.69);
		CustomColorSpace[2] = new Point(0.15, 0.06);
		UpdateSetting(AdjustType.Custom);
	}

	public void PhotoMode()
	{
		_wp = Illuminants.D65;
		_colorSpace = RGBWorkingSpaces.AdobeRGB1998;
		UpdateSetting(AdjustType.ColorSpace);
	}

	public void SetBrightness(double brightness)
	{
		_brightness = brightness;
	}

	public void SetColorTemp(double colortemp)
	{
		_kevlvin = Convert.ToInt32(colortemp);
	}

	public void SetGamma(double gamma)
	{
		_gamma = gamma;
	}

	public double GetGamma()
	{
		return _gamma;
	}

	public float GetColorTemp()
	{
		return _kevlvin;
	}

	public double GetBrightness()
	{
		return _brightness;
	}

	public double[] GetColorRGB()
	{
		double[] array = new double[3];
		for (int i = 0; i < 3; i++)
		{
			array[i] = ColorAdject[i];
		}
		return array;
	}

	private void UpdateSetting(AdjustType type)
	{
		InitColorStandard(_wp);
		colorTemperatureToRGB(_kevlvin);
		if (type.Equals(AdjustType.ColorSpace))
		{
			AdjustColorSpace(_colorSpace);
		}
		else if (type.Equals(AdjustType.Custom))
		{
			AdjustColorSpaceCustom(CustomColorSpace[0], CustomColorSpace[1], CustomColorSpace[2]);
		}
	}

	public void SetColor(double R, double G, double B)
	{
		ColorAdject[0] = R;
		ColorAdject[1] = G;
		ColorAdject[2] = B;
		Console.WriteLine("Set Color R {0}, G {1}, B {2}", ColorAdject[0], ColorAdject[1], ColorAdject[2]);
		Console.WriteLine("Set Color R {0}, G {1}, B {2}", ColorConvertToGammaMap(ColorAdject[0]), ColorConvertToGammaMap(ColorAdject[1]), ColorConvertToGammaMap(ColorAdject[2]));
	}

	public void ExecuteSettings()
	{
		foreach (ConnectedMonitors.MonitorInfo monitor in ConnectedMonitors.Monitors)
		{
			monitor.WithMonitorHdc(delegate(ConnectedMonitors.MonitorInfo m, IntPtr hdc)
			{
				UpdateRamps(hdc, _gamma, _brightness);
			});
		}
	}

	private double ColorConvertToGammaMap(double color)
	{
		return Math.Round(color / 2.0 - 127.0, 0);
	}

	private void AdjustColorSpaceCustom(Point R, Point G, Point B)
	{
		Point point = ColorXYZtoxy(_wp.X, _wp.Y, _wp.Z, 1.0);
		double num = Math.Sqrt(Math.Pow(point.X - R.X, 2.0) + Math.Pow(point.Y - R.Y, 2.0));
		double num2 = Math.Sqrt(Math.Pow(point.X - G.X, 2.0) + Math.Pow(point.Y - G.Y, 2.0));
		double num3 = Math.Sqrt(Math.Pow(point.X - B.X, 2.0) + Math.Pow(point.Y - B.Y, 2.0));
		ColorAdject[0] = Math.Round(num / RGBStandard["R"] * 255.0, 0);
		ColorAdject[1] = Math.Round(num2 / RGBStandard["G"] * 255.0, 0);
		ColorAdject[2] = Math.Round(num3 / RGBStandard["B"] * 255.0, 0);
		for (int i = 0; i < 3; i++)
		{
			ColorAdject[i] = Math.Round(ColorAdject[i] / 2.0, 0);
		}
		Console.WriteLine("Custom R {0}, G {1}, B {2}", ColorAdject[0], ColorAdject[1], ColorAdject[2]);
		foreach (ConnectedMonitors.MonitorInfo monitor in ConnectedMonitors.Monitors)
		{
			monitor.WithMonitorHdc(delegate(ConnectedMonitors.MonitorInfo m, IntPtr hdc)
			{
				UpdateRamps(hdc, _gamma, _brightness);
			});
		}
	}

	private void AdjustColorSpace(RGBWorkingSpace colorSpace)
	{
		RGBColor rGBColor = new RGBColor(1.0, 0.0, 0.0, colorSpace);
		new RGBColor(0.0, 1.0, 0.0, colorSpace);
		new RGBColor(0.0, 0.0, 1.0, colorSpace);
		Point wpxy = ColorXYZtoxy(_wp.X, _wp.Y, _wp.Z, 1.0);
		double num = Distance(wpxy, rGBColor.WorkingSpace.ChromaticityCoordinates.R);
		double num2 = Distance(wpxy, rGBColor.WorkingSpace.ChromaticityCoordinates.G);
		double num3 = Distance(wpxy, rGBColor.WorkingSpace.ChromaticityCoordinates.B);
		ColorAdject[0] = Math.Round(num / RGBStandard["R"] * 255.0, 0);
		ColorAdject[1] = Math.Round(num2 / RGBStandard["G"] * 255.0, 0);
		ColorAdject[2] = Math.Round(num3 / RGBStandard["B"] * 255.0, 0);
		for (int i = 0; i < 3; i++)
		{
			ColorAdject[i] = Math.Round(ColorAdject[i] / 2.0, 0);
		}
		Console.WriteLine("Default R {0}, G {1}, B {2}", ColorAdject[0], ColorAdject[1], ColorAdject[2]);
	}

	public bool UpdateRamps(IntPtr hdc, double m_gamma, double setbrightness, bool isIntel = false)
	{
		MonitorNativeWin32API.RAMP lpRamp = new MonitorNativeWin32API.RAMP
		{
			Red = new ushort[256],
			Green = new ushort[256],
			Blue = new ushort[256]
		};
		for (int i = 0; i < 3; i++)
		{
			for (int j = 0; j < 256; j++)
			{
				double num = ColorConvertToGammaMap(ColorAdject[i]);
				double num2 = Convert.ToDouble(ColortempatueRGB[i] / 2.0 - 127.0) + setbrightness * 1.28;
				if (num2 < 0.0)
				{
					num2 = 0.0;
				}
				double num3 = Convert.ToInt32(num + num2) * 255;
				double num4 = Math.Pow((double)j / 256.0, 1.0 / m_gamma) * 65535.0 + num3;
				if (num4 > 65535.0)
				{
					num4 = 65535.0;
				}
				if (num4 < 0.0)
				{
					num4 = 0.0;
				}
				switch (i)
				{
				case 0:
					lpRamp.Red[j] = (ushort)num4;
					break;
				case 1:
					lpRamp.Green[j] = (ushort)num4;
					break;
				case 2:
					lpRamp.Blue[j] = (ushort)num4;
					break;
				}
			}
		}
		return MonitorNativeWin32API.SetDeviceGammaRamp(hdc, ref lpRamp);
	}

	private void InitColorStandard(XYZColor wppoint)
	{
		RGBColor rgbColor = new RGBColor(1.0, 0.0, 0.0, RGBWorkingSpaces.CIERGB);
		RGBColor rGBColor = ColorSpaceConvert(rgbColor, RGBWorkingSpaces.CIERGB);
		Point wpxy = ColorXYZtoxy(wppoint.X, wppoint.Y, wppoint.Z, 1.0);
		double value = Distance(wpxy, rGBColor.WorkingSpace.ChromaticityCoordinates.R);
		double value2 = Distance(wpxy, rGBColor.WorkingSpace.ChromaticityCoordinates.G);
		double value3 = Distance(wpxy, rGBColor.WorkingSpace.ChromaticityCoordinates.B);
		RGBStandard.Clear();
		RGBStandard.Add("R", value);
		RGBStandard.Add("G", value2);
		RGBStandard.Add("B", value3);
	}

	private Point ColorXYZtoxy(double X, double Y, double Z, double Extendnubmer = 400.0)
	{
		double num = Math.Round(X / (X + Y + Z), 4);
		double num2 = Math.Round(Y / (X + Y + Z), 4);
		return new Point(num * Extendnubmer, num2 * Extendnubmer);
	}

	private RGBColor ColorSpaceConvert(RGBColor rgbColor, RGBWorkingSpace TargetSpace)
	{
		RGBColor color = rgbColor;
		return new ColourfulConverter
		{
			TargetRGBWorkingSpace = TargetSpace
		}.Adapt(in color);
	}

	private double Distance(Point wpxy, xyChromaticityCoordinates coordinate)
	{
		return Math.Sqrt(Math.Pow(wpxy.X - coordinate.x, 2.0) + Math.Pow(wpxy.Y - coordinate.y, 2.0));
	}

	private void colorTemperatureToRGB(int kelvin)
	{
		int num = kelvin / 100;
		double x2;
		double x;
		double d;
		if (num <= 66)
		{
			x = 255.0;
			d = num;
			d = 99.4708025861 * Math.Log(d) - 161.1195681661;
			if (num <= 19)
			{
				x2 = 0.0;
			}
			else
			{
				x2 = num - 10;
				x2 = 138.5177312231 * Math.Log(x2) - 305.0447927307;
			}
		}
		else
		{
			x = num - 60;
			x = 329.698727446 * Math.Pow(x, -0.1332047592);
			d = num - 60;
			d = 288.1221695283 * Math.Pow(d, -0.0755148492);
			x2 = 255.0;
		}
		ColortempatueRGB[0] = Math.Round(clamp(x, 0, 255), 0);
		ColortempatueRGB[1] = Math.Round(clamp(d, 0, 255), 0);
		ColortempatueRGB[2] = Math.Round(clamp(x2, 0, 255), 0);
	}

	private double clamp(double x, int min, int max)
	{
		if (x < (double)min)
		{
			return min;
		}
		if (x > (double)max)
		{
			return max;
		}
		return x;
	}
}
