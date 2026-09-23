using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Colourful.Implementation;
using Colourful.Implementation.Conversion;
using Colourful.Implementation.RGB;
using Microsoft.CodeAnalysis;

[assembly: CompilationRelaxations(8)]
[assembly: RuntimeCompatibility(WrapNonExceptionThrows = true)]
[assembly: Debuggable(DebuggableAttribute.DebuggingModes.IgnoreSymbolStoreSequencePoints)]
[assembly: CLSCompliant(true)]
[assembly: ComVisible(false)]
[assembly: Guid("d11f6be9-3dcb-45b7-a076-4d476236c3cb")]
[assembly: TargetFramework(".NETFramework,Version=v4.5", FrameworkDisplayName = ".NET Framework 4.5")]
[assembly: AssemblyCompany("Tomáš Pažourek")]
[assembly: AssemblyConfiguration("Release")]
[assembly: AssemblyCopyright("Tomáš Pažourek")]
[assembly: AssemblyDescription("Open source .NET library for working with color spaces.")]
[assembly: AssemblyFileVersion("2.0.5.150")]
[assembly: AssemblyInformationalVersion("2.0.5+a1b1ecb35e8a0cc3a2673359d2d5f244190a24bc")]
[assembly: AssemblyProduct("Colourful")]
[assembly: AssemblyTitle("Colourful")]
[assembly: AssemblyVersion("2.0.5.0")]
namespace Microsoft.CodeAnalysis
{
	[CompilerGenerated]
	[Embedded]
	internal sealed class EmbeddedAttribute : Attribute
	{
	}
}
namespace System.Runtime.CompilerServices
{
	[CompilerGenerated]
	[Embedded]
	internal sealed class IsReadOnlyAttribute : Attribute
	{
	}
}
namespace Colourful
{
	public readonly struct HunterLabColor : IColorVector
	{
		public static readonly XYZColor DefaultWhitePoint = Illuminants.C;

		private readonly XYZColor? _whitePoint;

		public double L { get; }

		public double a { get; }

		public double b { get; }

		public XYZColor WhitePoint => _whitePoint ?? DefaultWhitePoint;

		public IReadOnlyList<double> Vector => new double[3] { L, a, b };

		public HunterLabColor(double l, double a, double b)
			: this(l, a, b, DefaultWhitePoint)
		{
		}

		public HunterLabColor(double l, double a, double b, XYZColor whitePoint)
		{
			L = l;
			this.a = a;
			this.b = b;
			_whitePoint = whitePoint;
		}

		public HunterLabColor(IReadOnlyList<double> vector)
			: this(vector, DefaultWhitePoint)
		{
		}

		public HunterLabColor(IReadOnlyList<double> vector, XYZColor whitePoint)
			: this(vector[0], vector[1], vector[2], whitePoint)
		{
		}

		public bool Equals(HunterLabColor other)
		{
			if (L.Equals(other.L) && a.Equals(other.a))
			{
				return b.Equals(other.b);
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is HunterLabColor other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (((L.GetHashCode() * 397) ^ a.GetHashCode()) * 397) ^ b.GetHashCode();
		}

		public static bool operator ==(HunterLabColor left, HunterLabColor right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(HunterLabColor left, HunterLabColor right)
		{
			return !object.Equals(left, right);
		}

		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "HunterLab [L={0:0.##}, a={1:0.##}, b={2:0.##}]", new object[3] { L, a, b });
		}
	}
	public interface IColorVector
	{
		IReadOnlyList<double> Vector { get; }
	}
	public static class Illuminants
	{
		public static readonly XYZColor A = new XYZColor(1.0985, 1.0, 0.35585);

		public static readonly XYZColor B = new XYZColor(0.99072, 1.0, 0.85223);

		public static readonly XYZColor C = new XYZColor(0.98074, 1.0, 1.18232);

		public static readonly XYZColor D50 = new XYZColor(0.96422, 1.0, 0.82521);

		public static readonly XYZColor D55 = new XYZColor(0.95682, 1.0, 0.92149);

		public static readonly XYZColor D65 = new XYZColor(0.95047, 1.0, 1.08883);

		public static readonly XYZColor D75 = new XYZColor(0.94972, 1.0, 1.22638);

		public static readonly XYZColor E = new XYZColor(1.0, 1.0, 1.0);

		public static readonly XYZColor F2 = new XYZColor(0.99186, 1.0, 0.67393);

		public static readonly XYZColor F7 = new XYZColor(0.95041, 1.0, 1.08747);

		public static readonly XYZColor F11 = new XYZColor(1.00962, 1.0, 0.6435);
	}
	public interface IRGBWorkingSpace
	{
		XYZColor WhitePoint { get; }

		RGBPrimariesChromaticityCoordinates ChromaticityCoordinates { get; }

		ICompanding Companding { get; }
	}
	public readonly struct LabColor : IColorVector
	{
		public static readonly XYZColor DefaultWhitePoint = Illuminants.D50;

		private readonly XYZColor? _whitePoint;

		public double L { get; }

		public double a { get; }

		public double b { get; }

		public XYZColor WhitePoint => _whitePoint ?? DefaultWhitePoint;

		public IReadOnlyList<double> Vector => new double[3] { L, a, b };

		public LabColor(double l, double a, double b)
			: this(l, a, b, DefaultWhitePoint)
		{
		}

		public LabColor(double l, double a, double b, XYZColor whitePoint)
		{
			L = l;
			this.a = a;
			this.b = b;
			_whitePoint = whitePoint;
		}

		public LabColor(IReadOnlyList<double> vector)
			: this(vector, DefaultWhitePoint)
		{
		}

		public LabColor(IReadOnlyList<double> vector, XYZColor whitePoint)
			: this(vector[0], vector[1], vector[2], whitePoint)
		{
		}

		public bool Equals(LabColor other)
		{
			if (L == other.L && a == other.a)
			{
				return b == other.b;
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is LabColor other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (((L.GetHashCode() * 397) ^ a.GetHashCode()) * 397) ^ b.GetHashCode();
		}

		public static bool operator ==(LabColor left, LabColor right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LabColor left, LabColor right)
		{
			return !object.Equals(left, right);
		}

		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "Lab [L={0:0.##}, a={1:0.##}, b={2:0.##}]", new object[3] { L, a, b });
		}
	}
	public readonly struct LChabColor : IColorVector
	{
		public static readonly XYZColor DefaultWhitePoint = Illuminants.D50;

		private readonly XYZColor? _whitePoint;

		public double L { get; }

		public double C { get; }

		public double h { get; }

		public XYZColor WhitePoint => _whitePoint ?? DefaultWhitePoint;

		public IReadOnlyList<double> Vector => new double[3] { L, C, h };

		public double Saturation => SaturationLChFormulas.GetSaturation(L, C);

		public LChabColor(double l, double c, double h)
			: this(l, c, h, DefaultWhitePoint)
		{
		}

		public LChabColor(double l, double c, double h, XYZColor whitePoint)
		{
			L = l;
			C = c;
			this.h = h;
			_whitePoint = whitePoint;
		}

		public LChabColor(IReadOnlyList<double> vector)
			: this(vector, DefaultWhitePoint)
		{
		}

		public LChabColor(IReadOnlyList<double> vector, XYZColor whitePoint)
			: this(vector[0], vector[1], vector[2], whitePoint)
		{
		}

		public bool Equals(LChabColor other)
		{
			if (L == other.L && C == other.C)
			{
				return h == other.h;
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is LChabColor other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (((L.GetHashCode() * 397) ^ C.GetHashCode()) * 397) ^ h.GetHashCode();
		}

		public static bool operator ==(LChabColor left, LChabColor right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LChabColor left, LChabColor right)
		{
			return !object.Equals(left, right);
		}

		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "LChab [L={0:0.##}, C={1:0.##}, h={2:0.##}]", new object[3] { L, C, h });
		}
	}
	public readonly struct LChuvColor : IColorVector
	{
		public static readonly XYZColor DefaultWhitePoint = Illuminants.D65;

		private readonly XYZColor? _whitePoint;

		public double L { get; }

		public double C { get; }

		public double h { get; }

		public XYZColor WhitePoint => _whitePoint ?? DefaultWhitePoint;

		public IReadOnlyList<double> Vector => new double[3] { L, C, h };

		public double Saturation => SaturationLChFormulas.GetSaturation(L, C);

		public LChuvColor(double l, double c, double h)
			: this(l, c, h, DefaultWhitePoint)
		{
		}

		public LChuvColor(double l, double c, double h, XYZColor whitePoint)
		{
			L = l;
			C = c;
			this.h = h;
			_whitePoint = whitePoint;
		}

		public LChuvColor(IReadOnlyList<double> vector)
			: this(vector, DefaultWhitePoint)
		{
		}

		public LChuvColor(IReadOnlyList<double> vector, XYZColor whitePoint)
			: this(vector[0], vector[1], vector[2], whitePoint)
		{
		}

		public static LChuvColor FromSaturation(double lightness, double hue, double saturation)
		{
			double chroma = SaturationLChFormulas.GetChroma(saturation, lightness);
			return new LChuvColor(lightness, chroma, hue);
		}

		public bool Equals(LChuvColor other)
		{
			if (L == other.L && C == other.C)
			{
				return h == other.h;
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is LChuvColor other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (((L.GetHashCode() * 397) ^ C.GetHashCode()) * 397) ^ h.GetHashCode();
		}

		public static bool operator ==(LChuvColor left, LChuvColor right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LChuvColor left, LChuvColor right)
		{
			return !object.Equals(left, right);
		}

		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "LChuv [L={0:0.##}, C={1:0.##}, h={2:0.##}]", new object[3] { L, C, h });
		}
	}
	public readonly struct LinearRGBColor : IColorVector
	{
		public static readonly IRGBWorkingSpace DefaultWorkingSpace = RGBWorkingSpaces.sRGB;

		private readonly IRGBWorkingSpace _workingSpace;

		public double R { get; }

		public double G { get; }

		public double B { get; }

		public IReadOnlyList<double> Vector => new double[3] { R, G, B };

		public IRGBWorkingSpace WorkingSpace => _workingSpace ?? DefaultWorkingSpace;

		public LinearRGBColor(double r, double g, double b)
			: this(r, g, b, DefaultWorkingSpace)
		{
		}

		public LinearRGBColor(double r, double g, double b, IRGBWorkingSpace workingSpace)
		{
			R = r.CheckRange(0.0, 1.0);
			G = g.CheckRange(0.0, 1.0);
			B = b.CheckRange(0.0, 1.0);
			_workingSpace = workingSpace;
		}

		public LinearRGBColor(IReadOnlyList<double> vector)
			: this(vector, DefaultWorkingSpace)
		{
		}

		public LinearRGBColor(IReadOnlyList<double> vector, IRGBWorkingSpace workingSpace)
			: this(vector[0], vector[1], vector[2], workingSpace)
		{
		}

		public bool Equals(LinearRGBColor other)
		{
			if (R == other.R && G == other.G && B == other.B)
			{
				return WorkingSpace.Equals(other.WorkingSpace);
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is LinearRGBColor other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (base.GetHashCode() * 397) ^ WorkingSpace.GetHashCode();
		}

		public static bool operator ==(LinearRGBColor left, LinearRGBColor right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LinearRGBColor left, LinearRGBColor right)
		{
			return !object.Equals(left, right);
		}

		public static LinearRGBColor FromGrey(double value, IRGBWorkingSpace workingSpace)
		{
			return new LinearRGBColor(value, value, value, workingSpace);
		}

		public static LinearRGBColor FromGrey(double value)
		{
			return FromGrey(value, DefaultWorkingSpace);
		}

		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "LinearRGB [R={0:0.##}, G={1:0.##}, B={2:0.##}]", new object[3] { R, G, B });
		}
	}
	public readonly struct LMSColor : IColorVector
	{
		public double L { get; }

		public double M { get; }

		public double S { get; }

		public IReadOnlyList<double> Vector => new double[3] { L, M, S };

		public LMSColor(double l, double m, double s)
		{
			L = l;
			M = m;
			S = s;
		}

		public LMSColor(IReadOnlyList<double> vector)
			: this(vector[0], vector[1], vector[2])
		{
		}

		public bool Equals(LMSColor other)
		{
			if (L == other.L && M == other.M)
			{
				return S == other.S;
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is LMSColor other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (((L.GetHashCode() * 397) ^ M.GetHashCode()) * 397) ^ S.GetHashCode();
		}

		public static bool operator ==(LMSColor left, LMSColor right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LMSColor left, LMSColor right)
		{
			return !object.Equals(left, right);
		}

		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "LMS [L={0:0.##}, M={1:0.##}, S={2:0.##}]", new object[3] { L, M, S });
		}
	}
	public readonly struct LuvColor : IColorVector
	{
		public static readonly XYZColor DefaultWhitePoint = Illuminants.D65;

		private readonly XYZColor? _whitePoint;

		public double L { get; }

		public double u { get; }

		public double v { get; }

		public XYZColor WhitePoint => _whitePoint ?? DefaultWhitePoint;

		public IReadOnlyList<double> Vector => new double[3] { L, u, v };

		public LuvColor(double l, double u, double v)
			: this(l, u, v, DefaultWhitePoint)
		{
		}

		public LuvColor(double l, double u, double v, XYZColor whitePoint)
		{
			L = l;
			this.u = u;
			this.v = v;
			_whitePoint = whitePoint;
		}

		public LuvColor(IReadOnlyList<double> vector)
			: this(vector, DefaultWhitePoint)
		{
		}

		public LuvColor(IReadOnlyList<double> vector, XYZColor whitePoint)
			: this(vector[0], vector[1], vector[2], whitePoint)
		{
		}

		public bool Equals(LuvColor other)
		{
			if (L == other.L && u == other.u)
			{
				return v == other.v;
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is LuvColor other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (((L.GetHashCode() * 397) ^ u.GetHashCode()) * 397) ^ v.GetHashCode();
		}

		public static bool operator ==(LuvColor left, LuvColor right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LuvColor left, LuvColor right)
		{
			return !object.Equals(left, right);
		}

		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "Luv [L={0:0.##}, u={1:0.##}, v={2:0.##}]", new object[3] { L, u, v });
		}
	}
	public static class MacbethColorChecker
	{
		public static readonly RGBColor DarkSkin = RGBColor.FromRGB8bit(115, 82, 68, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor LightSkin = RGBColor.FromRGB8bit(194, 150, 130, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor BlueSky = RGBColor.FromRGB8bit(98, 122, 157, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Foliage = RGBColor.FromRGB8bit(87, 108, 67, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor BlueFlower = RGBColor.FromRGB8bit(133, 128, 177, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor BluishGreen = RGBColor.FromRGB8bit(103, 189, 170, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Orange = RGBColor.FromRGB8bit(214, 126, 44, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor PurplishBlue = RGBColor.FromRGB8bit(80, 91, 166, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor ModerateRed = RGBColor.FromRGB8bit(193, 90, 99, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Purple = RGBColor.FromRGB8bit(94, 60, 108, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor YellowGreen = RGBColor.FromRGB8bit(157, 188, 64, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor OrangeYellow = RGBColor.FromRGB8bit(224, 163, 46, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Blue = RGBColor.FromRGB8bit(56, 61, 150, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Green = RGBColor.FromRGB8bit(70, 148, 73, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Red = RGBColor.FromRGB8bit(175, 54, 60, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Yellow = RGBColor.FromRGB8bit(231, 199, 31, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Magenta = RGBColor.FromRGB8bit(187, 86, 149, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Cyan = RGBColor.FromRGB8bit(8, 133, 161, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor White = RGBColor.FromRGB8bit(243, 243, 242, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Neutral8 = RGBColor.FromRGB8bit(200, 200, 200, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Neutral6p5 = RGBColor.FromRGB8bit(160, 160, 160, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Neutral5 = RGBColor.FromRGB8bit(122, 122, 121, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Neutral3p5 = RGBColor.FromRGB8bit(85, 85, 85, RGBWorkingSpaces.sRGB);

		public static readonly RGBColor Black = RGBColor.FromRGB8bit(52, 52, 52, RGBWorkingSpaces.sRGB);

		public static readonly IReadOnlyList<RGBColor> Colors = new RGBColor[24]
		{
			DarkSkin, LightSkin, BlueSky, Foliage, BlueFlower, BluishGreen, Orange, PurplishBlue, ModerateRed, Purple,
			YellowGreen, OrangeYellow, Blue, Green, Red, Yellow, Magenta, Cyan, White, Neutral8,
			Neutral6p5, Neutral5, Neutral3p5, Black
		};
	}
	public readonly struct RGBColor : IColorVector, IEquatable<RGBColor>
	{
		public static readonly IRGBWorkingSpace DefaultWorkingSpace = RGBWorkingSpaces.sRGB;

		private readonly IRGBWorkingSpace _workingSpace;

		public double R { get; }

		public double G { get; }

		public double B { get; }

		public IReadOnlyList<double> Vector => new double[3] { R, G, B };

		public IRGBWorkingSpace WorkingSpace => _workingSpace ?? DefaultWorkingSpace;

		public RGBColor(double r, double g, double b)
			: this(r, g, b, DefaultWorkingSpace)
		{
		}

		public RGBColor(double r, double g, double b, IRGBWorkingSpace workingSpace)
		{
			R = r.CheckRange(0.0, 1.0);
			G = g.CheckRange(0.0, 1.0);
			B = b.CheckRange(0.0, 1.0);
			_workingSpace = workingSpace;
		}

		public RGBColor(IReadOnlyList<double> vector)
			: this(vector, DefaultWorkingSpace)
		{
		}

		public RGBColor(IReadOnlyList<double> vector, IRGBWorkingSpace workingSpace)
			: this(vector[0], vector[1], vector[2], workingSpace)
		{
		}

		public RGBColor(Color color)
			: this(color, DefaultWorkingSpace)
		{
		}

		public RGBColor(Color color, IRGBWorkingSpace workingSpace)
			: this((double)(int)color.R / 255.0, (double)(int)color.G / 255.0, (double)(int)color.B / 255.0, workingSpace)
		{
		}

		public bool Equals(RGBColor other)
		{
			if (R == other.R && G == other.G && B == other.B)
			{
				return WorkingSpace.Equals(other.WorkingSpace);
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is RGBColor other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (base.GetHashCode() * 397) ^ WorkingSpace.GetHashCode();
		}

		public static bool operator ==(RGBColor left, RGBColor right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(RGBColor left, RGBColor right)
		{
			return !object.Equals(left, right);
		}

		public static RGBColor FromGrey(double value, IRGBWorkingSpace workingSpace)
		{
			return new RGBColor(value, value, value, workingSpace);
		}

		public static RGBColor FromGrey(double value)
		{
			return FromGrey(value, DefaultWorkingSpace);
		}

		public static RGBColor FromRGB8bit(byte red, byte green, byte blue, IRGBWorkingSpace workingSpace)
		{
			return new RGBColor((double)(int)red / 255.0, (double)(int)green / 255.0, (double)(int)blue / 255.0, workingSpace);
		}

		public static RGBColor FromRGB8bit(byte red, byte green, byte blue)
		{
			return FromRGB8bit(red, green, blue, DefaultWorkingSpace);
		}

		public Color ToColor()
		{
			return this;
		}

		public static implicit operator Color(RGBColor input)
		{
			byte red = (byte)Math.Round(input.R * 255.0).CropRange(0.0, 255.0);
			byte green = (byte)Math.Round(input.G * 255.0).CropRange(0.0, 255.0);
			byte blue = (byte)Math.Round(input.B * 255.0).CropRange(0.0, 255.0);
			return Color.FromArgb(red, green, blue);
		}

		public static explicit operator RGBColor(Color color)
		{
			return new RGBColor(color);
		}

		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "RGB [R={0:0.##}, G={1:0.##}, B={2:0.##}]", new object[3] { R, G, B });
		}
	}
	public static class RGBWorkingSpaces
	{
		public static readonly RGBWorkingSpace sRGB = new RGBWorkingSpace(Illuminants.D65, new sRGBCompanding(), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.64, 0.33), new xyChromaticityCoordinates(0.3, 0.6), new xyChromaticityCoordinates(0.15, 0.06)));

		public static readonly RGBWorkingSpace sRGBSimplified = new RGBWorkingSpace(Illuminants.D65, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.64, 0.33), new xyChromaticityCoordinates(0.3, 0.6), new xyChromaticityCoordinates(0.15, 0.06)));

		public static readonly RGBWorkingSpace Rec709 = new RGBWorkingSpace(Illuminants.D65, new Rec709Companding(), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.64, 0.33), new xyChromaticityCoordinates(0.3, 0.6), new xyChromaticityCoordinates(0.15, 0.06)));

		public static readonly RGBWorkingSpace Rec2020 = new RGBWorkingSpace(Illuminants.D65, new Rec2020Companding(), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.708, 0.292), new xyChromaticityCoordinates(0.17, 0.797), new xyChromaticityCoordinates(0.131, 0.046)));

		public static readonly RGBWorkingSpace ECIRGBv2 = new RGBWorkingSpace(Illuminants.D50, new LCompanding(), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.67, 0.33), new xyChromaticityCoordinates(0.21, 0.71), new xyChromaticityCoordinates(0.14, 0.08)));

		public static readonly RGBWorkingSpace AdobeRGB1998 = new RGBWorkingSpace(Illuminants.D65, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.64, 0.33), new xyChromaticityCoordinates(0.21, 0.71), new xyChromaticityCoordinates(0.15, 0.06)));

		public static readonly RGBWorkingSpace ApplesRGB = new RGBWorkingSpace(Illuminants.D65, new GammaCompanding(1.8), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.625, 0.34), new xyChromaticityCoordinates(0.28, 0.595), new xyChromaticityCoordinates(0.155, 0.07)));

		public static readonly RGBWorkingSpace BestRGB = new RGBWorkingSpace(Illuminants.D50, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.7347, 0.2653), new xyChromaticityCoordinates(0.215, 0.775), new xyChromaticityCoordinates(0.13, 0.035)));

		public static readonly RGBWorkingSpace BetaRGB = new RGBWorkingSpace(Illuminants.D50, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.6888, 0.3112), new xyChromaticityCoordinates(0.1986, 0.7551), new xyChromaticityCoordinates(0.1265, 0.0352)));

		public static readonly RGBWorkingSpace BruceRGB = new RGBWorkingSpace(Illuminants.D65, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.64, 0.33), new xyChromaticityCoordinates(0.28, 0.65), new xyChromaticityCoordinates(0.15, 0.06)));

		public static readonly RGBWorkingSpace CIERGB = new RGBWorkingSpace(Illuminants.E, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.735, 0.265), new xyChromaticityCoordinates(0.274, 0.717), new xyChromaticityCoordinates(0.167, 0.009)));

		public static readonly RGBWorkingSpace ColorMatchRGB = new RGBWorkingSpace(Illuminants.D50, new GammaCompanding(1.8), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.63, 0.34), new xyChromaticityCoordinates(0.295, 0.605), new xyChromaticityCoordinates(0.15, 0.075)));

		public static readonly RGBWorkingSpace DonRGB4 = new RGBWorkingSpace(Illuminants.D50, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.696, 0.3), new xyChromaticityCoordinates(0.215, 0.765), new xyChromaticityCoordinates(0.13, 0.035)));

		public static readonly RGBWorkingSpace EktaSpacePS5 = new RGBWorkingSpace(Illuminants.D50, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.695, 0.305), new xyChromaticityCoordinates(0.26, 0.7), new xyChromaticityCoordinates(0.11, 0.005)));

		public static readonly RGBWorkingSpace NTSCRGB = new RGBWorkingSpace(Illuminants.C, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.67, 0.33), new xyChromaticityCoordinates(0.21, 0.71), new xyChromaticityCoordinates(0.14, 0.08)));

		public static readonly RGBWorkingSpace PALSECAMRGB = new RGBWorkingSpace(Illuminants.D65, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.64, 0.33), new xyChromaticityCoordinates(0.29, 0.6), new xyChromaticityCoordinates(0.15, 0.06)));

		public static readonly RGBWorkingSpace ProPhotoRGB = new RGBWorkingSpace(Illuminants.D50, new GammaCompanding(1.8), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.7347, 0.2653), new xyChromaticityCoordinates(0.1596, 0.8404), new xyChromaticityCoordinates(0.0366, 0.0001)));

		public static readonly RGBWorkingSpace SMPTECRGB = new RGBWorkingSpace(Illuminants.D65, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.63, 0.34), new xyChromaticityCoordinates(0.31, 0.595), new xyChromaticityCoordinates(0.155, 0.07)));

		public static readonly RGBWorkingSpace WideGamutRGB = new RGBWorkingSpace(Illuminants.D50, new GammaCompanding(2.2), new RGBPrimariesChromaticityCoordinates(new xyChromaticityCoordinates(0.735, 0.265), new xyChromaticityCoordinates(0.115, 0.826), new xyChromaticityCoordinates(0.157, 0.018)));
	}
	public readonly struct xyChromaticityCoordinates
	{
		public double x { get; }

		public double y { get; }

		public xyChromaticityCoordinates(double x, double y)
		{
			this.x = x;
			this.y = y;
		}

		public bool Equals(xyChromaticityCoordinates other)
		{
			if (x.Equals(other.x))
			{
				return y.Equals(other.y);
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is xyChromaticityCoordinates other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (x.GetHashCode() * 397) ^ y.GetHashCode();
		}

		public static bool operator ==(xyChromaticityCoordinates left, xyChromaticityCoordinates right)
		{
			return left.Equals(right);
		}

		public static bool operator !=(xyChromaticityCoordinates left, xyChromaticityCoordinates right)
		{
			return !left.Equals(right);
		}

		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "xy [x={0:0.##}, y={1:0.##}]", new object[2] { x, y });
		}
	}
	public readonly struct xyYColor : IColorVector
	{
		public double x => Chromaticity.x;

		public double y => Chromaticity.y;

		public double Luminance { get; }

		public xyChromaticityCoordinates Chromaticity { get; }

		public IReadOnlyList<double> Vector => new double[3] { x, y, Luminance };

		public xyYColor(double x, double y, double Y)
			: this(new xyChromaticityCoordinates(x, y), Y)
		{
		}

		public xyYColor(xyChromaticityCoordinates chromaticity, double Y)
		{
			Chromaticity = chromaticity;
			Luminance = Y;
		}

		public xyYColor(IReadOnlyList<double> vector)
			: this(vector[0], vector[1], vector[2])
		{
		}

		public bool Equals(xyYColor other)
		{
			if (x == other.x && y == other.y)
			{
				return Luminance == other.Luminance;
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is xyYColor other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (((x.GetHashCode() * 397) ^ y.GetHashCode()) * 397) ^ Luminance.GetHashCode();
		}

		public static bool operator ==(xyYColor left, xyYColor right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(xyYColor left, xyYColor right)
		{
			return !object.Equals(left, right);
		}

		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "xyY [x={0:0.##}, y={1:0.##}, Y={2:0.##}]", new object[3] { x, y, Luminance });
		}
	}
	public readonly struct XYZColor : IColorVector
	{
		public double X { get; }

		public double Y { get; }

		public double Z { get; }

		public IReadOnlyList<double> Vector => new double[3] { X, Y, Z };

		public XYZColor(double x, double y, double z)
		{
			X = x;
			Y = y;
			Z = z;
		}

		public XYZColor(IReadOnlyList<double> vector)
			: this(vector[0], vector[1], vector[2])
		{
		}

		public bool Equals(XYZColor other)
		{
			if (X == other.X && Y == other.Y)
			{
				return Z == other.Z;
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is XYZColor other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (((X.GetHashCode() * 397) ^ Y.GetHashCode()) * 397) ^ Z.GetHashCode();
		}

		public static bool operator ==(XYZColor left, XYZColor right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(XYZColor left, XYZColor right)
		{
			return !object.Equals(left, right);
		}

		public override string ToString()
		{
			return string.Format(CultureInfo.InvariantCulture, "XYZ [X={0:0.##}, Y={1:0.##}, Z={2:0.##}]", new object[3] { X, Y, Z });
		}
	}
	public static class CCTConverter
	{
		public static xyChromaticityCoordinates GetChromaticityOfCCT(double temperature)
		{
			double num = ((!(temperature <= 4000.0)) ? (-3.0258469 * (1000000000.0 / MathUtils.Pow3(temperature)) + 2.1070379 * (1000000.0 / MathUtils.Pow2(temperature)) + 0.2226347 * (1000.0 / temperature) + 0.24039) : (-0.2661239 * (1000000000.0 / MathUtils.Pow3(temperature)) - 0.234358 * (1000000.0 / MathUtils.Pow2(temperature)) + 0.8776956 * (1000.0 / temperature) + 0.17991));
			double y = ((temperature <= 2222.0) ? (-1.1063814 * MathUtils.Pow3(num) - 1.3481102 * MathUtils.Pow2(num) + 2.18555832 * num - 0.20219683) : ((!(temperature <= 4000.0)) ? (3.081758 * MathUtils.Pow3(num) - 5.8733867 * MathUtils.Pow2(num) + 3.75112997 * num - 0.37001483) : (-0.9549476 * MathUtils.Pow3(num) - 1.37418593 * MathUtils.Pow2(num) + 2.09137015 * num - 0.16748867)));
			return new xyChromaticityCoordinates(num, y);
		}

		public static double GetCCTOfChromaticity(in xyChromaticityCoordinates chromaticity)
		{
			double num = (chromaticity.x - 0.3366) / (chromaticity.y - 0.1735);
			return -949.86315 + 6253.80338 * Math.Exp((0.0 - num) / 0.92159) + 28.70599 * Math.Exp((0.0 - num) / 0.20039) + 4E-05 * Math.Exp((0.0 - num) / (57.0 / 800.0));
		}
	}
	internal static class SaturationLChFormulas
	{
		public static double GetSaturation(double L, double C)
		{
			double num = 100.0 * (C / L);
			if (double.IsNaN(num))
			{
				return 0.0;
			}
			return num;
		}

		public static double GetChroma(double saturation, double L)
		{
			return L * (saturation / 100.0);
		}
	}
}
namespace Colourful.Implementation
{
	internal static class Angle
	{
		private const double TwoPI = Math.PI * 2.0;

		public static double RadianToDegree(double rad)
		{
			return 360.0 * (rad / (Math.PI * 2.0));
		}

		public static double DegreeToRadian(double deg)
		{
			return Math.PI * 2.0 * (deg / 360.0);
		}

		public static double NormalizeDegree(double deg)
		{
			double num = deg % 360.0;
			if (!(num >= 0.0))
			{
				return num + 360.0;
			}
			return num;
		}
	}
	internal static class Extensions
	{
		public static double CheckRange(this double value, double min, double max)
		{
			if (value < min)
			{
				throw new ArgumentOutOfRangeException("value", value, "The minimum value is " + min);
			}
			if (value > max)
			{
				throw new ArgumentOutOfRangeException("value", value, "The maximum value is " + max);
			}
			return value;
		}

		public static double CropRange(this double value, double min, double max)
		{
			if (value < min)
			{
				return min;
			}
			if (value > max)
			{
				return max;
			}
			return value;
		}

		public static IReadOnlyList<double> CropRange(this IReadOnlyList<double> vector, double min, double max)
		{
			double[] array = new double[vector.Count];
			for (int i = 0; i < vector.Count; i++)
			{
				if (vector[i] < min)
				{
					array[i] = min;
				}
				else if (vector[i] > max)
				{
					array[i] = max;
				}
				else
				{
					array[i] = vector[i];
				}
			}
			return array;
		}

		public static IReadOnlyList<IReadOnlyList<double>> Inverse(this IReadOnlyList<IReadOnlyList<double>> matrix)
		{
			if (matrix.Count != 3 || matrix[0].Count != 3)
			{
				throw new ArgumentOutOfRangeException("matrix", "Inversion is supported only on 3 by 3 matrices.");
			}
			double num = matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1];
			double num2 = 0.0 - (matrix[0][1] * matrix[2][2] - matrix[0][2] * matrix[2][1]);
			double num3 = matrix[0][1] * matrix[1][2] - matrix[0][2] * matrix[1][1];
			double num4 = 0.0 - (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0]);
			double num5 = matrix[0][0] * matrix[2][2] - matrix[0][2] * matrix[2][0];
			double num6 = 0.0 - (matrix[0][0] * matrix[1][2] - matrix[0][2] * matrix[1][0]);
			double num7 = matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0];
			double num8 = 0.0 - (matrix[0][0] * matrix[2][1] - matrix[0][1] * matrix[2][0]);
			double num9 = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0];
			double num10 = matrix[0][0] * num + matrix[0][1] * num4 + matrix[0][2] * num7;
			return new IReadOnlyList<double>[3]
			{
				new double[3]
				{
					num / num10,
					num2 / num10,
					num3 / num10
				},
				new double[3]
				{
					num4 / num10,
					num5 / num10,
					num6 / num10
				},
				new double[3]
				{
					num7 / num10,
					num8 / num10,
					num9 / num10
				}
			};
		}

		public static IReadOnlyList<double> MultiplyBy(this IReadOnlyList<IReadOnlyList<double>> matrix, IReadOnlyList<double> vector)
		{
			if (matrix[0].Count != vector.Count)
			{
				throw new ArgumentOutOfRangeException("matrix", "Non-conformable matrices and vectors cannot be multiplied.");
			}
			double[] array = new double[matrix.Count];
			for (int i = 0; i < matrix.Count; i++)
			{
				for (int j = 0; j < vector.Count; j++)
				{
					array[i] += matrix[i][j] * vector[j];
				}
			}
			return array;
		}

		public static IReadOnlyList<IReadOnlyList<double>> MultiplyBy(this IReadOnlyList<IReadOnlyList<double>> matrix1, IReadOnlyList<IReadOnlyList<double>> matrix2)
		{
			if (matrix1[0].Count != matrix2.Count)
			{
				throw new ArgumentOutOfRangeException("matrix1", "Non-conformable matrices cannot be multiplied.");
			}
			double[][] array = MatrixFactory.CreateEmpty(matrix1.Count, matrix2[0].Count);
			for (int i = 0; i < matrix1.Count; i++)
			{
				for (int j = 0; j < matrix2[0].Count; j++)
				{
					for (int k = 0; k < matrix1[0].Count; k++)
					{
						array[i][j] += matrix1[i][k] * matrix2[k][j];
					}
				}
			}
			return array;
		}
	}
	internal static class MathUtils
	{
		public static double Pow2(double x)
		{
			return x * x;
		}

		public static double Pow3(double x)
		{
			return x * x * x;
		}

		public static double Pow4(double x)
		{
			return x * x * (x * x);
		}

		public static double Pow7(double x)
		{
			return x * x * x * (x * x * x) * x;
		}

		public static double SinDeg(double x)
		{
			return Math.Sin(Angle.DegreeToRadian(x));
		}

		public static double CosDeg(double x)
		{
			return Math.Cos(Angle.DegreeToRadian(x));
		}
	}
	internal static class MatrixFactory
	{
		public static double[][] CreateEmpty(int rows, int columns)
		{
			double[][] array = new double[rows][];
			for (int i = 0; i < rows; i++)
			{
				array[i] = new double[columns];
			}
			return array;
		}

		public static IReadOnlyList<IReadOnlyList<double>> CreateIdentity(int size)
		{
			double[][] array = new double[size][];
			for (int i = 0; i < size; i++)
			{
				array[i] = new double[size];
				array[i][i] = 1.0;
			}
			return array;
		}

		public static IReadOnlyList<IReadOnlyList<double>> CreateDiagonal(params double[] items)
		{
			int num = items.Length;
			double[][] array = new double[num][];
			for (int i = 0; i < num; i++)
			{
				array[i] = new double[num];
				array[i][i] = items[i];
			}
			return array;
		}
	}
}
namespace Colourful.Implementation.RGB
{
	public sealed class GammaCompanding : ICompanding
	{
		public double Gamma { get; }

		public GammaCompanding(double gamma)
		{
			Gamma = gamma;
		}

		public double InverseCompanding(double channel)
		{
			return Math.Pow(channel, Gamma);
		}

		public double Companding(double channel)
		{
			return Math.Pow(channel, 1.0 / Gamma);
		}

		public bool Equals(GammaCompanding other)
		{
			if (other == null)
			{
				return false;
			}
			return Gamma == other.Gamma;
		}

		public override bool Equals(object obj)
		{
			if (obj is GammaCompanding other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return Gamma.GetHashCode();
		}

		public static bool operator ==(GammaCompanding left, GammaCompanding right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(GammaCompanding left, GammaCompanding right)
		{
			return !object.Equals(left, right);
		}
	}
	public interface ICompanding
	{
		double InverseCompanding(double channel);

		double Companding(double channel);
	}
	public sealed class LCompanding : ICompanding
	{
		private const double Kappa = 903.2962962962963;

		private const double Epsilon = 0.008856451679035631;

		public double InverseCompanding(double channel)
		{
			if (!(channel <= 0.08))
			{
				return Math.Pow((channel + 0.16) / 1.16, 3.0);
			}
			return 100.0 * channel / 903.2962962962963;
		}

		public double Companding(double channel)
		{
			if (!(channel <= 0.008856451679035631))
			{
				return 1.16 * Math.Pow(channel, 1.0 / 3.0) - 0.16;
			}
			return channel * 903.2962962962963 / 100.0;
		}

		public override bool Equals(object obj)
		{
			return obj is LCompanding;
		}

		public override int GetHashCode()
		{
			return 1;
		}

		public static bool operator ==(LCompanding left, LCompanding right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LCompanding left, LCompanding right)
		{
			return !object.Equals(left, right);
		}
	}
	public sealed class Rec2020Companding : ICompanding
	{
		private const double Alpha = 1.09929682680944;

		private const double Beta = 0.018053968510807;

		private const double InverseBeta = 0.08124285829863151;

		public double InverseCompanding(double channel)
		{
			if (!(channel < 0.08124285829863151))
			{
				return Math.Pow((channel + 1.09929682680944 - 1.0) / 1.09929682680944, 2.2222222222222223);
			}
			return channel / 4.5;
		}

		public double Companding(double channel)
		{
			if (!(channel < 0.018053968510807))
			{
				return 1.09929682680944 * Math.Pow(channel, 0.45) - 0.09929682680944008;
			}
			return 4.5 * channel;
		}
	}
	public sealed class Rec709Companding : ICompanding
	{
		public double InverseCompanding(double channel)
		{
			if (!(channel < 0.081))
			{
				return Math.Pow((channel + 0.099) / 1.099, 2.2222222222222223);
			}
			return channel / 4.5;
		}

		public double Companding(double channel)
		{
			if (!(channel < 0.018))
			{
				return 1.099 * Math.Pow(channel, 0.45) - 0.099;
			}
			return 4.5 * channel;
		}
	}
	public readonly struct RGBPrimariesChromaticityCoordinates
	{
		public xyChromaticityCoordinates R { get; }

		public xyChromaticityCoordinates G { get; }

		public xyChromaticityCoordinates B { get; }

		public RGBPrimariesChromaticityCoordinates(xyChromaticityCoordinates r, xyChromaticityCoordinates g, xyChromaticityCoordinates b)
		{
			R = r;
			G = g;
			B = b;
		}

		public bool Equals(RGBPrimariesChromaticityCoordinates other)
		{
			if (R.Equals(other.R) && G.Equals(other.G))
			{
				return B.Equals(other.B);
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is RGBPrimariesChromaticityCoordinates other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (((R.GetHashCode() * 397) ^ G.GetHashCode()) * 397) ^ B.GetHashCode();
		}

		public static bool operator ==(RGBPrimariesChromaticityCoordinates left, RGBPrimariesChromaticityCoordinates right)
		{
			return left.Equals(right);
		}

		public static bool operator !=(RGBPrimariesChromaticityCoordinates left, RGBPrimariesChromaticityCoordinates right)
		{
			return !left.Equals(right);
		}
	}
	public sealed class RGBWorkingSpace : IRGBWorkingSpace
	{
		public XYZColor WhitePoint { get; }

		public RGBPrimariesChromaticityCoordinates ChromaticityCoordinates { get; }

		public ICompanding Companding { get; }

		public RGBWorkingSpace(XYZColor referenceWhite, ICompanding companding, RGBPrimariesChromaticityCoordinates chromaticityCoordinates)
		{
			WhitePoint = referenceWhite;
			Companding = companding;
			ChromaticityCoordinates = chromaticityCoordinates;
		}

		public bool Equals(IRGBWorkingSpace other)
		{
			if (other == null)
			{
				return false;
			}
			if (this == other)
			{
				return true;
			}
			if (object.Equals(WhitePoint, other.WhitePoint) && ChromaticityCoordinates.Equals(other.ChromaticityCoordinates))
			{
				return Companding.Equals(other.Companding);
			}
			return false;
		}

		public override bool Equals(object obj)
		{
			if (obj is IRGBWorkingSpace other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return (((WhitePoint.GetHashCode() * 397) ^ ChromaticityCoordinates.GetHashCode()) * 397) ^ ((Companding != null) ? Companding.GetHashCode() : 0);
		}

		public static bool operator ==(RGBWorkingSpace left, RGBWorkingSpace right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(RGBWorkingSpace left, RGBWorkingSpace right)
		{
			return !object.Equals(left, right);
		}
	}
	public sealed class sRGBCompanding : ICompanding
	{
		public double InverseCompanding(double channel)
		{
			if (!(channel <= 0.04045))
			{
				return Math.Pow((channel + 0.055) / 1.055, 2.4);
			}
			return channel / 12.92;
		}

		public double Companding(double channel)
		{
			if (!(channel <= 0.0031308))
			{
				return 1.055 * Math.Pow(channel, 5.0 / 12.0) - 0.055;
			}
			return 12.92 * channel;
		}

		public override bool Equals(object obj)
		{
			return obj is sRGBCompanding;
		}

		public override int GetHashCode()
		{
			return 1;
		}

		public static bool operator ==(sRGBCompanding left, sRGBCompanding right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(sRGBCompanding left, sRGBCompanding right)
		{
			return !object.Equals(left, right);
		}
	}
}
namespace Colourful.Implementation.Conversion
{
	internal static class CIEConstants
	{
		public const double Epsilon = 0.008856451679035631;

		public const double Kappa = 903.2962962962963;
	}
	public sealed class HunterLabToXYZConverter : XYZAndHunterLabConverterBase, IColorConversion<HunterLabColor, XYZColor>
	{
		public static readonly HunterLabToXYZConverter Default = new HunterLabToXYZConverter();

		public XYZColor Convert(in HunterLabColor input)
		{
			double l = input.L;
			double a = input.a;
			double b = input.b;
			double x = input.WhitePoint.X;
			double y = input.WhitePoint.Y;
			double z = input.WhitePoint.Z;
			double num = XYZAndHunterLabConverterBase.ComputeKa(input.WhitePoint);
			double num2 = XYZAndHunterLabConverterBase.ComputeKb(input.WhitePoint);
			double num3 = MathUtils.Pow2(l / 100.0) * y;
			double x2 = (a / num * Math.Sqrt(num3 / y) + num3 / y) * x;
			double z2 = (b / num2 * Math.Sqrt(num3 / y) - num3 / y) * (0.0 - z);
			return new XYZColor(x2, num3, z2);
		}

		public override bool Equals(object obj)
		{
			return obj is HunterLabToXYZConverter;
		}

		public override int GetHashCode()
		{
			return 1;
		}

		public static bool operator ==(HunterLabToXYZConverter left, HunterLabToXYZConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(HunterLabToXYZConverter left, HunterLabToXYZConverter right)
		{
			return !object.Equals(left, right);
		}

		XYZColor IColorConversion<HunterLabColor, XYZColor>.Convert(in HunterLabColor input)
		{
			return Convert(in input);
		}
	}
	public abstract class XYZAndHunterLabConverterBase
	{
		protected static double ComputeKa(XYZColor whitePoint)
		{
			if (whitePoint == Illuminants.C)
			{
				return 175.0;
			}
			return 88.36598666935973 * (whitePoint.X + whitePoint.Y);
		}

		protected static double ComputeKb(XYZColor whitePoint)
		{
			if (whitePoint == Illuminants.C)
			{
				return 70.0;
			}
			return 32.09389757461831 * (whitePoint.Y + whitePoint.Z);
		}
	}
	public sealed class XYZToHunterLabConverter : XYZAndHunterLabConverterBase, IColorConversion<XYZColor, HunterLabColor>
	{
		public XYZColor HunterLabWhitePoint { get; }

		public XYZToHunterLabConverter()
			: this(HunterLabColor.DefaultWhitePoint)
		{
		}

		public XYZToHunterLabConverter(XYZColor labWhitePoint)
		{
			HunterLabWhitePoint = labWhitePoint;
		}

		public HunterLabColor Convert(in XYZColor input)
		{
			double x = input.X;
			double y = input.Y;
			double z = input.Z;
			double x2 = HunterLabWhitePoint.X;
			double y2 = HunterLabWhitePoint.Y;
			double z2 = HunterLabWhitePoint.Z;
			double num = XYZAndHunterLabConverterBase.ComputeKa(HunterLabWhitePoint);
			double num2 = XYZAndHunterLabConverterBase.ComputeKb(HunterLabWhitePoint);
			double l = 100.0 * Math.Sqrt(y / y2);
			double num3 = num * ((x / x2 - y / y2) / Math.Sqrt(y / y2));
			double num4 = num2 * ((y / y2 - z / z2) / Math.Sqrt(y / y2));
			if (double.IsNaN(num3))
			{
				num3 = 0.0;
			}
			if (double.IsNaN(num4))
			{
				num4 = 0.0;
			}
			return new HunterLabColor(l, num3, num4, HunterLabWhitePoint);
		}

		HunterLabColor IColorConversion<XYZColor, HunterLabColor>.Convert(in XYZColor input)
		{
			return Convert(in input);
		}
	}
	public interface IColorConversion<TInput, TOutput> where TInput : struct where TOutput : struct
	{
		TOutput Convert(in TInput input);
	}
	public sealed class LabToXYZConverter : IColorConversion<LabColor, XYZColor>
	{
		public static readonly LabToXYZConverter Default = new LabToXYZConverter();

		public XYZColor Convert(in LabColor input)
		{
			double l = input.L;
			double a = input.a;
			double b = input.b;
			double num = (l + 16.0) / 116.0;
			double num2 = a / 500.0 + num;
			double num3 = num - b / 200.0;
			double num4 = MathUtils.Pow3(num2);
			double num5 = MathUtils.Pow3(num3);
			double value = ((num4 > 0.008856451679035631) ? num4 : ((116.0 * num2 - 16.0) / 903.2962962962963));
			double value2 = ((l > 8.0) ? MathUtils.Pow3((l + 16.0) / 116.0) : (l / 903.2962962962963));
			double value3 = ((num5 > 0.008856451679035631) ? num5 : ((116.0 * num3 - 16.0) / 903.2962962962963));
			double x = input.WhitePoint.X;
			double y = input.WhitePoint.Y;
			double z = input.WhitePoint.Z;
			value = value.CropRange(0.0, 1.0);
			value2 = value2.CropRange(0.0, 1.0);
			double num6 = value3.CropRange(0.0, 1.0);
			double x2 = value * x;
			double y2 = value2 * y;
			double z2 = num6 * z;
			return new XYZColor(x2, y2, z2);
		}

		public override bool Equals(object obj)
		{
			return obj is LabToXYZConverter;
		}

		public override int GetHashCode()
		{
			return 1;
		}

		public static bool operator ==(LabToXYZConverter left, LabToXYZConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LabToXYZConverter left, LabToXYZConverter right)
		{
			return !object.Equals(left, right);
		}

		XYZColor IColorConversion<LabColor, XYZColor>.Convert(in LabColor input)
		{
			return Convert(in input);
		}
	}
	public sealed class XYZToLabConverter : IColorConversion<XYZColor, LabColor>
	{
		public XYZColor LabWhitePoint { get; }

		public XYZToLabConverter()
			: this(LabColor.DefaultWhitePoint)
		{
		}

		public XYZToLabConverter(XYZColor labWhitePoint)
		{
			LabWhitePoint = labWhitePoint;
		}

		public LabColor Convert(in XYZColor input)
		{
			double x = LabWhitePoint.X;
			double y = LabWhitePoint.Y;
			double z = LabWhitePoint.Z;
			double cr = input.X / x;
			double cr2 = input.Y / y;
			double cr3 = input.Z / z;
			double num = f(cr);
			double num2 = f(cr2);
			double num3 = f(cr3);
			double l = 116.0 * num2 - 16.0;
			double a = 500.0 * (num - num2);
			double b = 200.0 * (num2 - num3);
			return new LabColor(l, a, b, LabWhitePoint);
		}

		private static double f(double cr)
		{
			if (!(cr > 0.008856451679035631))
			{
				return (903.2962962962963 * cr + 16.0) / 116.0;
			}
			return Math.Pow(cr, 1.0 / 3.0);
		}

		public bool Equals(XYZToLabConverter other)
		{
			if (other == null)
			{
				return false;
			}
			if ((object)this != other)
			{
				return LabWhitePoint.Equals(other.LabWhitePoint);
			}
			return true;
		}

		public override bool Equals(object obj)
		{
			if (obj is XYZToLabConverter other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return LabWhitePoint.GetHashCode();
		}

		public static bool operator ==(XYZToLabConverter left, XYZToLabConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(XYZToLabConverter left, XYZToLabConverter right)
		{
			return !object.Equals(left, right);
		}

		LabColor IColorConversion<XYZColor, LabColor>.Convert(in XYZColor input)
		{
			return Convert(in input);
		}
	}
	public sealed class LabToLChabConverter : IColorConversion<LabColor, LChabColor>
	{
		public static readonly LabToLChabConverter Default = new LabToLChabConverter();

		public LChabColor Convert(in LabColor input)
		{
			double l = input.L;
			double a = input.a;
			double b = input.b;
			double c = Math.Sqrt(a * a + b * b);
			double h = Angle.NormalizeDegree(Angle.RadianToDegree(Math.Atan2(b, a)));
			return new LChabColor(l, c, h, input.WhitePoint);
		}

		public override bool Equals(object obj)
		{
			return obj is LabToLChabConverter;
		}

		public override int GetHashCode()
		{
			return 1;
		}

		public static bool operator ==(LabToLChabConverter left, LabToLChabConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LabToLChabConverter left, LabToLChabConverter right)
		{
			return !object.Equals(left, right);
		}

		LChabColor IColorConversion<LabColor, LChabColor>.Convert(in LabColor input)
		{
			return Convert(in input);
		}
	}
	public sealed class LChabToLabConverter : IColorConversion<LChabColor, LabColor>
	{
		public static readonly LChabToLabConverter Default = new LChabToLabConverter();

		public LabColor Convert(in LChabColor input)
		{
			double l = input.L;
			double c = input.C;
			double num = Angle.DegreeToRadian(input.h);
			double a = c * Math.Cos(num);
			double b = c * Math.Sin(num);
			return new LabColor(l, a, b, input.WhitePoint);
		}

		public override bool Equals(object obj)
		{
			return obj is LChabToLabConverter;
		}

		public override int GetHashCode()
		{
			return 1;
		}

		public static bool operator ==(LChabToLabConverter left, LChabToLabConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LChabToLabConverter left, LChabToLabConverter right)
		{
			return !object.Equals(left, right);
		}

		LabColor IColorConversion<LChabColor, LabColor>.Convert(in LChabColor input)
		{
			return Convert(in input);
		}
	}
	public sealed class LChuvToLuvConverter : IColorConversion<LChuvColor, LuvColor>
	{
		public static readonly LChuvToLuvConverter Default = new LChuvToLuvConverter();

		public LuvColor Convert(in LChuvColor input)
		{
			double l = input.L;
			double c = input.C;
			double num = Angle.DegreeToRadian(input.h);
			double u = c * Math.Cos(num);
			double v = c * Math.Sin(num);
			return new LuvColor(l, u, v, input.WhitePoint);
		}

		public override bool Equals(object obj)
		{
			return obj is LChuvToLuvConverter;
		}

		public override int GetHashCode()
		{
			return 1;
		}

		public static bool operator ==(LChuvToLuvConverter left, LChuvToLuvConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LChuvToLuvConverter left, LChuvToLuvConverter right)
		{
			return !object.Equals(left, right);
		}

		LuvColor IColorConversion<LChuvColor, LuvColor>.Convert(in LChuvColor input)
		{
			return Convert(in input);
		}
	}
	public sealed class LuvToLChuvConverter : IColorConversion<LuvColor, LChuvColor>
	{
		public static readonly LuvToLChuvConverter Default = new LuvToLChuvConverter();

		public LChuvColor Convert(in LuvColor input)
		{
			double l = input.L;
			double u = input.u;
			double v = input.v;
			double c = Math.Sqrt(u * u + v * v);
			double h = Angle.NormalizeDegree(Angle.RadianToDegree(Math.Atan2(v, u)));
			return new LChuvColor(l, c, h, input.WhitePoint);
		}

		public override bool Equals(object obj)
		{
			return obj is LuvToLChuvConverter;
		}

		public override int GetHashCode()
		{
			return 1;
		}

		public static bool operator ==(LuvToLChuvConverter left, LuvToLChuvConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LuvToLChuvConverter left, LuvToLChuvConverter right)
		{
			return !object.Equals(left, right);
		}

		LChuvColor IColorConversion<LuvColor, LChuvColor>.Convert(in LuvColor input)
		{
			return Convert(in input);
		}
	}
	public static class LMSTransformationMatrix
	{
		public static readonly IReadOnlyList<IReadOnlyList<double>> VonKriesHPEAdjusted = new IReadOnlyList<double>[3]
		{
			new double[3] { 0.40024, 0.7076, -0.08081 },
			new double[3] { -0.2263, 1.16532, 0.0457 },
			new double[3] { 0.0, 0.0, 0.91822 }
		};

		public static readonly IReadOnlyList<IReadOnlyList<double>> VonKriesHPE = new IReadOnlyList<double>[3]
		{
			new double[3] { 0.3897, 0.689, -0.0787 },
			new double[3] { -0.2298, 1.1834, 0.0464 },
			new double[3] { 0.0, 0.0, 1.0 }
		};

		public static readonly IReadOnlyList<IReadOnlyList<double>> XYZScaling = MatrixFactory.CreateIdentity(3);

		public static readonly IReadOnlyList<IReadOnlyList<double>> Bradford = new IReadOnlyList<double>[3]
		{
			new double[3] { 0.8951, 0.2664, -0.1614 },
			new double[3] { -0.7502, 1.7135, 0.0367 },
			new double[3] { 0.0389, -0.0685, 1.0296 }
		};

		public static readonly IReadOnlyList<IReadOnlyList<double>> BradfordSharp = new IReadOnlyList<double>[3]
		{
			new double[3] { 1.2694, -0.0988, -0.1706 },
			new double[3] { -0.8364, 1.8006, 0.0357 },
			new double[3] { 0.0297, -0.0315, 1.0018 }
		};

		public static readonly IReadOnlyList<IReadOnlyList<double>> CMCCAT2000 = new IReadOnlyList<double>[3]
		{
			new double[3] { 0.7982, 0.3389, -0.1371 },
			new double[3] { -0.5918, 1.5512, 0.0406 },
			new double[3] { 0.0008, 0.239, 0.9753 }
		};

		public static readonly IReadOnlyList<IReadOnlyList<double>> CAT02 = new IReadOnlyList<double>[3]
		{
			new double[3] { 0.7328, 0.4296, -0.1624 },
			new double[3] { -0.7036, 1.6975, 0.0061 },
			new double[3] { 0.003, 0.0136, 0.9834 }
		};
	}
	public sealed class XYZAndLMSConverter : IColorConversion<XYZColor, LMSColor>, IColorConversion<LMSColor, XYZColor>
	{
		public static readonly IReadOnlyList<IReadOnlyList<double>> DefaultTransformationMatrix = LMSTransformationMatrix.Bradford;

		private IReadOnlyList<IReadOnlyList<double>> _transformationMatrix;

		private IReadOnlyList<IReadOnlyList<double>> _transformationMatrixInverse;

		public IReadOnlyList<IReadOnlyList<double>> TransformationMatrix
		{
			get
			{
				return _transformationMatrix;
			}
			internal set
			{
				_transformationMatrix = value;
				_transformationMatrixInverse = TransformationMatrix.Inverse();
			}
		}

		public XYZAndLMSConverter()
			: this(DefaultTransformationMatrix)
		{
		}

		public XYZAndLMSConverter(IReadOnlyList<IReadOnlyList<double>> transformationMatrix)
		{
			TransformationMatrix = transformationMatrix;
		}

		public XYZColor Convert(in LMSColor input)
		{
			IReadOnlyList<double> vector = _transformationMatrixInverse.MultiplyBy(input.Vector);
			return new XYZColor(vector);
		}

		public LMSColor Convert(in XYZColor input)
		{
			IReadOnlyList<double> vector = TransformationMatrix.MultiplyBy(input.Vector);
			return new LMSColor(vector);
		}

		LMSColor IColorConversion<XYZColor, LMSColor>.Convert(in XYZColor input)
		{
			return Convert(in input);
		}

		XYZColor IColorConversion<LMSColor, XYZColor>.Convert(in LMSColor input)
		{
			return Convert(in input);
		}
	}
	public sealed class LuvToXYZConverter : IColorConversion<LuvColor, XYZColor>
	{
		public static readonly LuvToXYZConverter Default = new LuvToXYZConverter();

		public XYZColor Convert(in LuvColor input)
		{
			double l = input.L;
			double u = input.u;
			double v = input.v;
			double num = Compute_u0(input.WhitePoint);
			double num2 = Compute_v0(input.WhitePoint);
			double num3 = ((l > 8.0) ? MathUtils.Pow3((l + 16.0) / 116.0) : (l / 903.2962962962963));
			double num4 = (52.0 * l / (u + 13.0 * l * num) - 1.0) / 3.0;
			double num5 = -5.0 * num3;
			double num6 = -1.0 / 3.0;
			double num7 = (num3 * (39.0 * l / (v + 13.0 * l * num2) - 5.0) - num5) / (num4 - num6);
			double num8 = num7 * num4 + num5;
			if (double.IsNaN(num7) || num7 < 0.0)
			{
				num7 = 0.0;
			}
			if (double.IsNaN(num3) || num3 < 0.0)
			{
				num3 = 0.0;
			}
			if (double.IsNaN(num8) || num8 < 0.0)
			{
				num8 = 0.0;
			}
			return new XYZColor(num7, num3, num8);
		}

		private static double Compute_u0(XYZColor input)
		{
			return 4.0 * input.X / (input.X + 15.0 * input.Y + 3.0 * input.Z);
		}

		private static double Compute_v0(XYZColor input)
		{
			return 9.0 * input.Y / (input.X + 15.0 * input.Y + 3.0 * input.Z);
		}

		public override bool Equals(object obj)
		{
			return obj is LuvToXYZConverter;
		}

		public override int GetHashCode()
		{
			return 1;
		}

		public static bool operator ==(LuvToXYZConverter left, LuvToXYZConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LuvToXYZConverter left, LuvToXYZConverter right)
		{
			return !object.Equals(left, right);
		}

		XYZColor IColorConversion<LuvColor, XYZColor>.Convert(in LuvColor input)
		{
			return Convert(in input);
		}
	}
	public sealed class XYZToLuvConverter : IColorConversion<XYZColor, LuvColor>
	{
		public XYZColor LuvWhitePoint { get; }

		public XYZToLuvConverter()
			: this(LuvColor.DefaultWhitePoint)
		{
		}

		public XYZToLuvConverter(XYZColor labWhitePoint)
		{
			LuvWhitePoint = labWhitePoint;
		}

		public LuvColor Convert(in XYZColor input)
		{
			double num = input.Y / LuvWhitePoint.Y;
			double num2 = Compute_up(input);
			double num3 = Compute_vp(input);
			double num4 = Compute_up(LuvWhitePoint);
			double num5 = Compute_vp(LuvWhitePoint);
			double num6 = ((num > 0.008856451679035631) ? (116.0 * Math.Pow(num, 1.0 / 3.0) - 16.0) : (903.2962962962963 * num));
			if (double.IsNaN(num6) || num6 < 0.0)
			{
				num6 = 0.0;
			}
			double num7 = 13.0 * num6 * (num2 - num4);
			double num8 = 13.0 * num6 * (num3 - num5);
			if (double.IsNaN(num7))
			{
				num7 = 0.0;
			}
			if (double.IsNaN(num8))
			{
				num8 = 0.0;
			}
			return new LuvColor(num6, num7, num8, LuvWhitePoint);
		}

		private static double Compute_up(XYZColor input)
		{
			return 4.0 * input.X / (input.X + 15.0 * input.Y + 3.0 * input.Z);
		}

		private static double Compute_vp(XYZColor input)
		{
			return 9.0 * input.Y / (input.X + 15.0 * input.Y + 3.0 * input.Z);
		}

		public bool Equals(XYZToLuvConverter other)
		{
			if (other == null)
			{
				return false;
			}
			if ((object)this != other)
			{
				return LuvWhitePoint.Equals(other.LuvWhitePoint);
			}
			return true;
		}

		public override bool Equals(object obj)
		{
			if (obj is XYZToLuvConverter other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return LuvWhitePoint.GetHashCode();
		}

		public static bool operator ==(XYZToLuvConverter left, XYZToLuvConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(XYZToLuvConverter left, XYZToLuvConverter right)
		{
			return !object.Equals(left, right);
		}

		LuvColor IColorConversion<XYZColor, LuvColor>.Convert(in XYZColor input)
		{
			return Convert(in input);
		}
	}
	public abstract class LinearRGBAndXYZConverterBase
	{
		protected static IReadOnlyList<IReadOnlyList<double>> GetRGBToXYZMatrix(IRGBWorkingSpace workingSpace)
		{
			if (workingSpace == null)
			{
				throw new ArgumentNullException("workingSpace");
			}
			RGBPrimariesChromaticityCoordinates chromaticityCoordinates = workingSpace.ChromaticityCoordinates;
			double x = chromaticityCoordinates.R.x;
			double x2 = chromaticityCoordinates.G.x;
			double x3 = chromaticityCoordinates.B.x;
			double y = chromaticityCoordinates.R.y;
			double y2 = chromaticityCoordinates.G.y;
			double y3 = chromaticityCoordinates.B.y;
			double num = x / y;
			double num2 = (1.0 - x - y) / y;
			double num3 = x2 / y2;
			double num4 = (1.0 - x2 - y2) / y2;
			double num5 = x3 / y3;
			double num6 = (1.0 - x3 - y3) / y3;
			IReadOnlyList<IReadOnlyList<double>> matrix = new IReadOnlyList<double>[3]
			{
				new double[3] { num, num3, num5 },
				new double[3] { 1.0, 1.0, 1.0 },
				new double[3] { num2, num4, num6 }
			}.Inverse();
			IReadOnlyList<double> vector = workingSpace.WhitePoint.Vector;
			IReadOnlyList<double> readOnlyList = matrix.MultiplyBy(vector);
			double num7 = readOnlyList[0];
			double num8 = readOnlyList[1];
			double num9 = readOnlyList[2];
			return new IReadOnlyList<double>[3]
			{
				new double[3]
				{
					num7 * num,
					num8 * num3,
					num9 * num5
				},
				new double[3]
				{
					num7 * 1.0,
					num8 * 1.0,
					num9 * 1.0
				},
				new double[3]
				{
					num7 * num2,
					num8 * num4,
					num9 * num6
				}
			};
		}

		protected static IReadOnlyList<IReadOnlyList<double>> GetXYZToRGBMatrix(IRGBWorkingSpace workingSpace)
		{
			return GetRGBToXYZMatrix(workingSpace).Inverse();
		}
	}
	public sealed class LinearRGBToRGBConverter : IColorConversion<LinearRGBColor, RGBColor>
	{
		public static readonly LinearRGBToRGBConverter Default = new LinearRGBToRGBConverter();

		public RGBColor Convert(in LinearRGBColor input)
		{
			return CompandVector(input.Vector, input.WorkingSpace);
		}

		private static RGBColor CompandVector(IReadOnlyList<double> uncompandedVector, IRGBWorkingSpace workingSpace)
		{
			ICompanding companding = workingSpace.Companding;
			IReadOnlyList<double> vector = new double[3]
			{
				companding.Companding(uncompandedVector[0]).CropRange(0.0, 1.0),
				companding.Companding(uncompandedVector[1]).CropRange(0.0, 1.0),
				companding.Companding(uncompandedVector[2]).CropRange(0.0, 1.0)
			};
			return new RGBColor(vector, workingSpace);
		}

		public bool Equals(LinearRGBToRGBConverter other)
		{
			return other != null;
		}

		public override bool Equals(object obj)
		{
			return obj is LinearRGBToRGBConverter;
		}

		public override int GetHashCode()
		{
			return 1;
		}

		public static bool operator ==(LinearRGBToRGBConverter left, LinearRGBToRGBConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LinearRGBToRGBConverter left, LinearRGBToRGBConverter right)
		{
			return !object.Equals(left, right);
		}

		RGBColor IColorConversion<LinearRGBColor, RGBColor>.Convert(in LinearRGBColor input)
		{
			return Convert(in input);
		}
	}
	public sealed class LinearRGBToXYZConverter : LinearRGBAndXYZConverterBase, IColorConversion<LinearRGBColor, XYZColor>
	{
		private readonly IReadOnlyList<IReadOnlyList<double>> _conversionMatrix;

		public IRGBWorkingSpace SourceRGBWorkingSpace { get; }

		public LinearRGBToXYZConverter(IRGBWorkingSpace sourceRGBWorkingSpace)
		{
			SourceRGBWorkingSpace = sourceRGBWorkingSpace;
			_conversionMatrix = LinearRGBAndXYZConverterBase.GetRGBToXYZMatrix(SourceRGBWorkingSpace);
		}

		public XYZColor Convert(in LinearRGBColor input)
		{
			if (!object.Equals(input.WorkingSpace, SourceRGBWorkingSpace))
			{
				throw new InvalidOperationException("Working space of input RGB color must be equal to converter source RGB working space.");
			}
			IReadOnlyList<double> vector = _conversionMatrix.MultiplyBy(input.Vector);
			return new XYZColor(vector);
		}

		public bool Equals(LinearRGBToXYZConverter other)
		{
			if ((object)this == other)
			{
				return true;
			}
			return object.Equals(SourceRGBWorkingSpace, other.SourceRGBWorkingSpace);
		}

		public override bool Equals(object obj)
		{
			if (obj is LinearRGBToXYZConverter other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return SourceRGBWorkingSpace?.GetHashCode() ?? 0;
		}

		public static bool operator ==(LinearRGBToXYZConverter left, LinearRGBToXYZConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(LinearRGBToXYZConverter left, LinearRGBToXYZConverter right)
		{
			return !object.Equals(left, right);
		}

		XYZColor IColorConversion<LinearRGBColor, XYZColor>.Convert(in LinearRGBColor input)
		{
			return Convert(in input);
		}
	}
	public sealed class RGBToLinearRGBConverter : IColorConversion<RGBColor, LinearRGBColor>
	{
		public static readonly RGBToLinearRGBConverter Default = new RGBToLinearRGBConverter();

		public LinearRGBColor Convert(in RGBColor input)
		{
			IReadOnlyList<double> vector = UncompandVector(in input);
			return new LinearRGBColor(vector, input.WorkingSpace);
		}

		private static IReadOnlyList<double> UncompandVector(in RGBColor rgbColor)
		{
			ICompanding companding = rgbColor.WorkingSpace.Companding;
			IReadOnlyList<double> vector = rgbColor.Vector;
			return new double[3]
			{
				companding.InverseCompanding(vector[0]).CropRange(0.0, 1.0),
				companding.InverseCompanding(vector[1]).CropRange(0.0, 1.0),
				companding.InverseCompanding(vector[2]).CropRange(0.0, 1.0)
			};
		}

		public bool Equals(RGBToLinearRGBConverter other)
		{
			return other != null;
		}

		public override bool Equals(object obj)
		{
			return obj is RGBToLinearRGBConverter;
		}

		public override int GetHashCode()
		{
			return 1;
		}

		public static bool operator ==(RGBToLinearRGBConverter left, RGBToLinearRGBConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(RGBToLinearRGBConverter left, RGBToLinearRGBConverter right)
		{
			return !object.Equals(left, right);
		}

		LinearRGBColor IColorConversion<RGBColor, LinearRGBColor>.Convert(in RGBColor input)
		{
			return Convert(in input);
		}
	}
	public sealed class XYZToLinearRGBConverter : LinearRGBAndXYZConverterBase, IColorConversion<XYZColor, LinearRGBColor>
	{
		private readonly IReadOnlyList<IReadOnlyList<double>> _conversionMatrix;

		public IRGBWorkingSpace TargetRGBWorkingSpace { get; }

		public XYZToLinearRGBConverter()
			: this(null)
		{
		}

		public XYZToLinearRGBConverter(IRGBWorkingSpace targetRGBWorkingSpace)
		{
			TargetRGBWorkingSpace = targetRGBWorkingSpace ?? RGBColor.DefaultWorkingSpace;
			_conversionMatrix = LinearRGBAndXYZConverterBase.GetXYZToRGBMatrix(TargetRGBWorkingSpace);
		}

		public LinearRGBColor Convert(in XYZColor input)
		{
			IReadOnlyList<double> vector = input.Vector;
			IReadOnlyList<double> vector2 = _conversionMatrix.MultiplyBy(vector).CropRange(0.0, 1.0);
			return new LinearRGBColor(vector2, TargetRGBWorkingSpace);
		}

		public bool Equals(XYZToLinearRGBConverter other)
		{
			if (other == null)
			{
				return false;
			}
			if ((object)this != other)
			{
				return TargetRGBWorkingSpace.Equals(other.TargetRGBWorkingSpace);
			}
			return true;
		}

		public override bool Equals(object obj)
		{
			if (obj is XYZToLinearRGBConverter other)
			{
				return Equals(other);
			}
			return false;
		}

		public override int GetHashCode()
		{
			return TargetRGBWorkingSpace?.GetHashCode() ?? 0;
		}

		public static bool operator ==(XYZToLinearRGBConverter left, XYZToLinearRGBConverter right)
		{
			return object.Equals(left, right);
		}

		public static bool operator !=(XYZToLinearRGBConverter left, XYZToLinearRGBConverter right)
		{
			return !object.Equals(left, right);
		}

		LinearRGBColor IColorConversion<XYZColor, LinearRGBColor>.Convert(in XYZColor input)
		{
			return Convert(in input);
		}
	}
	public sealed class xyYAndXYZConverter : IColorConversion<XYZColor, xyYColor>, IColorConversion<xyYColor, XYZColor>
	{
		public static readonly xyYAndXYZConverter Default = new xyYAndXYZConverter();

		public XYZColor Convert(in xyYColor input)
		{
			if (input.y == 0.0)
			{
				return new XYZColor(0.0, 0.0, input.Luminance);
			}
			double x = input.x * input.Luminance / input.y;
			double luminance = input.Luminance;
			double z = (1.0 - input.x - input.y) * luminance / input.y;
			return new XYZColor(x, luminance, z);
		}

		public xyYColor Convert(in XYZColor input)
		{
			double num = input.X / (input.X + input.Y + input.Z);
			double num2 = input.Y / (input.X + input.Y + input.Z);
			if (double.IsNaN(num) || double.IsNaN(num2))
			{
				return new xyYColor(0.0, 0.0, input.Y);
			}
			double y = input.Y;
			return new xyYColor(num, num2, y);
		}

		xyYColor IColorConversion<XYZColor, xyYColor>.Convert(in XYZColor input)
		{
			return Convert(in input);
		}

		XYZColor IColorConversion<xyYColor, XYZColor>.Convert(in xyYColor input)
		{
			return Convert(in input);
		}
	}
}
namespace Colourful.Difference
{
	public sealed class CIE76ColorDifference : IColorDifference<LabColor>
	{
		public double ComputeDifference(in LabColor x, in LabColor y)
		{
			if (x.WhitePoint != y.WhitePoint)
			{
				throw new ArgumentException("Colors must have same white point to be compared.");
			}
			return Math.Sqrt((x.L - y.L) * (x.L - y.L) + (x.a - y.a) * (x.a - y.a) + (x.b - y.b) * (x.b - y.b));
		}

		double IColorDifference<LabColor>.ComputeDifference(in LabColor x, in LabColor y)
		{
			return ComputeDifference(in x, in y);
		}
	}
	public sealed class CIE94ColorDifference : IColorDifference<LabColor>
	{
		private const double KH = 1.0;

		private const double KC = 1.0;

		private readonly double K1;

		private readonly double K2;

		private readonly double KL;

		public CIE94ColorDifference()
			: this(CIE94ColorDifferenceApplication.GraphicArts)
		{
		}

		public CIE94ColorDifference(CIE94ColorDifferenceApplication application)
		{
			switch (application)
			{
			case CIE94ColorDifferenceApplication.GraphicArts:
				KL = 1.0;
				K1 = 0.045;
				K2 = 0.015;
				break;
			case CIE94ColorDifferenceApplication.Textiles:
				KL = 2.0;
				K1 = 0.048;
				K2 = 0.014;
				break;
			default:
				throw new ArgumentOutOfRangeException("application");
			}
		}

		public double ComputeDifference(in LabColor x, in LabColor y)
		{
			if (x.WhitePoint != y.WhitePoint)
			{
				throw new ArgumentException("Colors must have same white point to be compared.");
			}
			double num = x.a - y.a;
			double num2 = x.b - y.b;
			double num3 = x.L - y.L;
			double num4 = Math.Sqrt(x.a * x.a + x.b * x.b);
			double num5 = Math.Sqrt(y.a * y.a + y.b * y.b);
			double num6 = num4 - num5;
			double num7 = num * num + num2 * num2 - num6 * num6;
			double num8 = 1.0 + K1 * num4;
			double num9 = 1.0 + K2 * num4;
			return Math.Sqrt(MathUtils.Pow2(num3 / (KL * 1.0)) + MathUtils.Pow2(num6 / (1.0 * num8)) + num7 / MathUtils.Pow2(1.0 * num9));
		}

		double IColorDifference<LabColor>.ComputeDifference(in LabColor x, in LabColor y)
		{
			return ComputeDifference(in x, in y);
		}
	}
	public enum CIE94ColorDifferenceApplication
	{
		GraphicArts,
		Textiles
	}
	public sealed class CIEDE2000ColorDifference : IColorDifference<LabColor>
	{
		private const double k_H = 1.0;

		private const double k_L = 1.0;

		private const double k_C = 1.0;

		public double ComputeDifference(in LabColor x, in LabColor y)
		{
			if (x.WhitePoint != y.WhitePoint)
			{
				throw new ArgumentException("Colors must have same white point to be compared.");
			}
			Calculate_a_prime(x.a, y.a, x.b, y.b, out var a_prime, out var a_prime2);
			Calculate_C_prime(a_prime, a_prime2, x.b, y.b, out var C_prime, out var C_prime2);
			Calculate_h_prime(a_prime, a_prime2, x.b, y.b, out var h_prime, out var h_prime2);
			double num = y.L - x.L;
			double num2 = C_prime2 - C_prime;
			double num3 = Calculate_dh_prime(C_prime, C_prime2, h_prime, h_prime2);
			double num4 = 2.0 * Math.Sqrt(C_prime * C_prime2) * MathUtils.SinDeg(num3 / 2.0);
			double num5 = (x.L + y.L) / 2.0;
			double num6 = (C_prime + C_prime2) / 2.0;
			double num7 = Calculate_h_prime_mean(h_prime, h_prime2, C_prime, C_prime2);
			double num8 = 1.0 - 0.17 * MathUtils.CosDeg(num7 - 30.0) + 0.24 * MathUtils.CosDeg(2.0 * num7) + 0.32 * MathUtils.CosDeg(3.0 * num7 + 6.0) - 0.2 * MathUtils.CosDeg(4.0 * num7 - 63.0);
			double num9 = 30.0 * Math.Exp(0.0 - MathUtils.Pow2((num7 - 275.0) / 25.0));
			double num10 = 2.0 * Math.Sqrt(MathUtils.Pow7(num6) / (MathUtils.Pow7(num6) + MathUtils.Pow7(25.0)));
			double num11 = 1.0 + 0.015 * MathUtils.Pow2(num5 - 50.0) / Math.Sqrt(20.0 + MathUtils.Pow2(num5 - 50.0));
			double num12 = 1.0 + 0.045 * num6;
			double num13 = 1.0 + 0.015 * num6 * num8;
			double num14 = (0.0 - MathUtils.SinDeg(2.0 * num9)) * num10;
			return Math.Sqrt(MathUtils.Pow2(num / (1.0 * num11)) + MathUtils.Pow2(num2 / (1.0 * num12)) + MathUtils.Pow2(num4 / (1.0 * num13)) + num14 * (num2 / (1.0 * num12)) * (num4 / (1.0 * num13)));
		}

		private static void Calculate_a_prime(double a0, double a1, double b0, double b1, out double a_prime0, out double a_prime1)
		{
			double num = Math.Sqrt(a0 * a0 + b0 * b0);
			double num2 = Math.Sqrt(a1 * a1 + b1 * b1);
			double x = (num + num2) / 2.0;
			double num3 = 0.5 * (1.0 - Math.Sqrt(MathUtils.Pow7(x) / (MathUtils.Pow7(x) + MathUtils.Pow7(25.0))));
			a_prime0 = (1.0 + num3) * a0;
			a_prime1 = (1.0 + num3) * a1;
		}

		private static void Calculate_C_prime(double a_prime0, double a_prime1, double b0, double b1, out double C_prime0, out double C_prime1)
		{
			C_prime0 = Math.Sqrt(a_prime0 * a_prime0 + b0 * b0);
			C_prime1 = Math.Sqrt(a_prime1 * a_prime1 + b1 * b1);
		}

		private static void Calculate_h_prime(double a_prime0, double a_prime1, double b0, double b1, out double h_prime0, out double h_prime1)
		{
			double num = Angle.NormalizeDegree(Angle.RadianToDegree(Math.Atan2(b0, a_prime0)));
			h_prime0 = num;
			num = Angle.NormalizeDegree(Angle.RadianToDegree(Math.Atan2(b1, a_prime1)));
			h_prime1 = num;
		}

		private static double Calculate_dh_prime(double C_prime0, double C_prime1, double h_prime0, double h_prime1)
		{
			if (C_prime0 * C_prime1 == 0.0)
			{
				return 0.0;
			}
			if (Math.Abs(h_prime1 - h_prime0) <= 180.0)
			{
				return h_prime1 - h_prime0;
			}
			if (h_prime1 - h_prime0 > 180.0)
			{
				return h_prime1 - h_prime0 - 360.0;
			}
			if (h_prime1 - h_prime0 < -180.0)
			{
				return h_prime1 - h_prime0 + 360.0;
			}
			return 0.0;
		}

		private static double Calculate_h_prime_mean(double h_prime0, double h_prime1, double C_prime0, double C_prime1)
		{
			if (C_prime0 * C_prime1 == 0.0)
			{
				return h_prime0 + h_prime1;
			}
			if (Math.Abs(h_prime0 - h_prime1) <= 180.0)
			{
				return (h_prime0 + h_prime1) / 2.0;
			}
			if (Math.Abs(h_prime0 - h_prime1) > 180.0 && h_prime0 + h_prime1 < 360.0)
			{
				return (h_prime0 + h_prime1 + 360.0) / 2.0;
			}
			if (Math.Abs(h_prime0 - h_prime1) > 180.0 && h_prime0 + h_prime1 >= 360.0)
			{
				return (h_prime0 + h_prime1 - 360.0) / 2.0;
			}
			return h_prime0 + h_prime1;
		}

		double IColorDifference<LabColor>.ComputeDifference(in LabColor x, in LabColor y)
		{
			return ComputeDifference(in x, in y);
		}
	}
	public sealed class CMCColorDifference : IColorDifference<LabColor>
	{
		private readonly double _c;

		private readonly double _l;

		public CMCColorDifference(CMCColorDifferenceThreshold threshold)
		{
			switch (threshold)
			{
			case CMCColorDifferenceThreshold.Acceptability:
				_l = 2.0;
				_c = 1.0;
				break;
			case CMCColorDifferenceThreshold.Imperceptibility:
				_l = 1.0;
				_c = 1.0;
				break;
			default:
				throw new ArgumentOutOfRangeException("threshold");
			}
		}

		public CMCColorDifference(double lightness, double chroma)
		{
			_l = lightness;
			_c = chroma;
		}

		public double ComputeDifference(in LabColor x, in LabColor y)
		{
			double l = x.L;
			double a = x.a;
			double b = x.b;
			double l2 = y.L;
			double a2 = y.a;
			double b2 = y.b;
			double num = l - l2;
			double num2 = a - a2;
			double num3 = b - b2;
			double num4 = Math.Sqrt(a * a + b * b);
			double num5 = Math.Sqrt(a2 * a2 + b2 * b2);
			double num6 = num4 - num5;
			double num7 = num2 * num2 + num3 * num3 - num6 * num6;
			double num8 = Angle.NormalizeDegree(Angle.RadianToDegree(Math.Atan2(b, a)));
			double num9 = MathUtils.Pow4(num4);
			double num10 = Math.Sqrt(num9 / (num9 + 1900.0));
			double num11 = ((num8 >= 164.0 && num8 <= 345.0) ? (0.56 + Math.Abs(0.2 * MathUtils.CosDeg(num8 + 168.0))) : (0.36 + Math.Abs(0.4 * MathUtils.CosDeg(num8 + 35.0))));
			double num12 = 0.0638 * num4 / (1.0 + 0.0131 * num4) + 0.638;
			double num13 = ((l < 16.0) ? 0.511 : (0.040975 * l / (1.0 + 0.01765 * l)));
			double num14 = num12 * (num10 * num11 + 1.0 - num10);
			double num15 = num / (_l * num13);
			double num16 = num6 / (_c * num12);
			double num17 = num7 / (num14 * num14);
			return Math.Sqrt(num15 * num15 + num16 * num16 + num17);
		}

		double IColorDifference<LabColor>.ComputeDifference(in LabColor x, in LabColor y)
		{
			return ComputeDifference(in x, in y);
		}
	}
	public enum CMCColorDifferenceThreshold
	{
		Acceptability,
		Imperceptibility
	}
	public interface IColorDifference<TColor> where TColor : struct
	{
		double ComputeDifference(in TColor x, in TColor y);
	}
}
namespace Colourful.Conversion
{
	public class ColourfulConverter
	{
		public static readonly XYZColor DefaultWhitePoint = Illuminants.D65;

		private IReadOnlyList<IReadOnlyList<double>> _transformationMatrix;

		private XYZAndLMSConverter _cachedXYZAndLMSConverter;

		private XYZToLinearRGBConverter _lastXYZToLinearRGBConverter;

		private LinearRGBToXYZConverter _lastLinearRGBToXYZConverter;

		private bool IsChromaticAdaptationPerformed => ChromaticAdaptation != null;

		public IChromaticAdaptation ChromaticAdaptation { get; set; }

		public IReadOnlyList<IReadOnlyList<double>> LMSTransformationMatrix
		{
			get
			{
				return _transformationMatrix;
			}
			set
			{
				_transformationMatrix = value;
				if (_cachedXYZAndLMSConverter == null)
				{
					_cachedXYZAndLMSConverter = new XYZAndLMSConverter(value);
				}
				else
				{
					_cachedXYZAndLMSConverter.TransformationMatrix = value;
				}
			}
		}

		public XYZColor WhitePoint { get; set; }

		public XYZColor TargetLabWhitePoint { get; set; }

		public XYZColor TargetLuvWhitePoint { get; set; }

		public XYZColor TargetHunterLabWhitePoint { get; set; }

		public IRGBWorkingSpace TargetRGBWorkingSpace { get; set; }

		public XYZColor Adapt(in XYZColor color, in XYZColor sourceWhitePoint)
		{
			if (!IsChromaticAdaptationPerformed)
			{
				throw new InvalidOperationException("Cannot perform chromatic adaptation, provide chromatic adaptation method and white point.");
			}
			return ChromaticAdaptation.Transform(in color, in sourceWhitePoint, WhitePoint);
		}

		public LinearRGBColor Adapt(in LinearRGBColor color)
		{
			if (!IsChromaticAdaptationPerformed)
			{
				throw new InvalidOperationException("Cannot perform chromatic adaptation, provide chromatic adaptation method and white point.");
			}
			if (color.WorkingSpace.Equals(TargetRGBWorkingSpace))
			{
				return color;
			}
			XYZColor sourceColor = GetLinearRGBToXYZConverter(color.WorkingSpace).Convert(in color);
			XYZColor input = ChromaticAdaptation.Transform(in sourceColor, color.WorkingSpace.WhitePoint, TargetRGBWorkingSpace.WhitePoint);
			return GetXYZToLinearRGBConverter(TargetRGBWorkingSpace).Convert(in input);
		}

		public RGBColor Adapt(in RGBColor color)
		{
			return ToRGB(Adapt(ToLinearRGB(in color)));
		}

		public LabColor Adapt(in LabColor color)
		{
			if (!IsChromaticAdaptationPerformed)
			{
				throw new InvalidOperationException("Cannot perform chromatic adaptation, provide chromatic adaptation method and white point.");
			}
			if (color.WhitePoint.Equals(TargetLabWhitePoint))
			{
				return color;
			}
			return ToLab(ToXYZ(in color));
		}

		public LChabColor Adapt(in LChabColor color)
		{
			if (!IsChromaticAdaptationPerformed)
			{
				throw new InvalidOperationException("Cannot perform chromatic adaptation, provide chromatic adaptation method and white point.");
			}
			if (color.WhitePoint.Equals(TargetLabWhitePoint))
			{
				return color;
			}
			return ToLChab(ToLab(in color));
		}

		public HunterLabColor Adapt(in HunterLabColor color)
		{
			if (!IsChromaticAdaptationPerformed)
			{
				throw new InvalidOperationException("Cannot perform chromatic adaptation, provide chromatic adaptation method and white point.");
			}
			if (color.WhitePoint.Equals(TargetHunterLabWhitePoint))
			{
				return color;
			}
			return ToHunterLab(ToXYZ(in color));
		}

		public LuvColor Adapt(in LuvColor color)
		{
			if (!IsChromaticAdaptationPerformed)
			{
				throw new InvalidOperationException("Cannot perform chromatic adaptation, provide chromatic adaptation method and white point.");
			}
			if (color.WhitePoint.Equals(TargetLuvWhitePoint))
			{
				return color;
			}
			return ToLuv(ToXYZ(in color));
		}

		public ColourfulConverter()
		{
			WhitePoint = DefaultWhitePoint;
			LMSTransformationMatrix = XYZAndLMSConverter.DefaultTransformationMatrix;
			ChromaticAdaptation = new VonKriesChromaticAdaptation(_cachedXYZAndLMSConverter, _cachedXYZAndLMSConverter);
			TargetLabWhitePoint = LabColor.DefaultWhitePoint;
			TargetHunterLabWhitePoint = HunterLabColor.DefaultWhitePoint;
			TargetLuvWhitePoint = LuvColor.DefaultWhitePoint;
			TargetRGBWorkingSpace = RGBColor.DefaultWorkingSpace;
		}

		public HunterLabColor ToHunterLab(in RGBColor color)
		{
			return ToHunterLab(ToXYZ(in color));
		}

		public HunterLabColor ToHunterLab(in LinearRGBColor color)
		{
			return ToHunterLab(ToXYZ(in color));
		}

		public HunterLabColor ToHunterLab(in XYZColor color)
		{
			XYZColor input = ((!WhitePoint.Equals(TargetHunterLabWhitePoint) && IsChromaticAdaptationPerformed) ? ChromaticAdaptation.Transform(in color, WhitePoint, TargetHunterLabWhitePoint) : color);
			return new XYZToHunterLabConverter(TargetHunterLabWhitePoint).Convert(in input);
		}

		public HunterLabColor ToHunterLab(in xyYColor color)
		{
			return ToHunterLab(ToXYZ(in color));
		}

		public HunterLabColor ToHunterLab(in LabColor color)
		{
			return ToHunterLab(ToXYZ(in color));
		}

		public HunterLabColor ToHunterLab(in LChabColor color)
		{
			return ToHunterLab(ToXYZ(in color));
		}

		public HunterLabColor ToHunterLab(in LuvColor color)
		{
			return ToHunterLab(ToXYZ(in color));
		}

		public HunterLabColor ToHunterLab(in LChuvColor color)
		{
			return ToHunterLab(ToXYZ(in color));
		}

		public HunterLabColor ToHunterLab(in LMSColor color)
		{
			return ToHunterLab(ToXYZ(in color));
		}

		public HunterLabColor ToHunterLab<T>(T color) where T : struct, IColorVector
		{
			if (!(color is RGBColor color2))
			{
				if (!(color is LinearRGBColor color3))
				{
					if (!(color is XYZColor color4))
					{
						if (!(color is xyYColor color5))
						{
							if (color is HunterLabColor)
							{
								object obj = color;
								return (HunterLabColor)((obj is HunterLabColor) ? obj : null);
							}
							if (!(color is LabColor color6))
							{
								if (!(color is LChabColor color7))
								{
									if (!(color is LuvColor color8))
									{
										if (!(color is LChuvColor color9))
										{
											if (color is LMSColor color10)
											{
												return ToHunterLab(in color10);
											}
											throw new ArgumentException($"Cannot accept type '{typeof(T)}'.", "color");
										}
										return ToHunterLab(in color9);
									}
									return ToHunterLab(in color8);
								}
								return ToHunterLab(in color7);
							}
							return ToHunterLab(in color6);
						}
						return ToHunterLab(in color5);
					}
					return ToHunterLab(in color4);
				}
				return ToHunterLab(in color3);
			}
			return ToHunterLab(in color2);
		}

		public LabColor ToLab(in RGBColor color)
		{
			return ToLab(ToXYZ(in color));
		}

		public LabColor ToLab(in LinearRGBColor color)
		{
			return ToLab(ToXYZ(in color));
		}

		public LabColor ToLab(in XYZColor color)
		{
			XYZColor input = ((!WhitePoint.Equals(TargetLabWhitePoint) && IsChromaticAdaptationPerformed) ? ChromaticAdaptation.Transform(in color, WhitePoint, TargetLabWhitePoint) : color);
			return new XYZToLabConverter(TargetLabWhitePoint).Convert(in input);
		}

		public LabColor ToLab(in xyYColor color)
		{
			return ToLab(ToXYZ(in color));
		}

		public LabColor ToLab(in LChabColor color)
		{
			LabColor color2 = LChabToLabConverter.Default.Convert(in color);
			if (!IsChromaticAdaptationPerformed)
			{
				return color2;
			}
			return Adapt(in color2);
		}

		public LabColor ToLab(in HunterLabColor color)
		{
			return ToLab(ToXYZ(in color));
		}

		public LabColor ToLab(in LuvColor color)
		{
			return ToLab(ToXYZ(in color));
		}

		public LabColor ToLab(in LChuvColor color)
		{
			return ToLab(ToXYZ(in color));
		}

		public LabColor ToLab(in LMSColor color)
		{
			return ToLab(ToXYZ(in color));
		}

		public LabColor ToLab<T>(T color) where T : struct, IColorVector
		{
			if (!(color is RGBColor color2))
			{
				if (!(color is LinearRGBColor color3))
				{
					if (!(color is XYZColor color4))
					{
						if (!(color is xyYColor color5))
						{
							if (!(color is HunterLabColor color6))
							{
								if (color is LabColor)
								{
									object obj = color;
									return (LabColor)((obj is LabColor) ? obj : null);
								}
								if (!(color is LChabColor color7))
								{
									if (!(color is LuvColor color8))
									{
										if (!(color is LChuvColor color9))
										{
											if (color is LMSColor color10)
											{
												return ToLab(in color10);
											}
											throw new ArgumentException($"Cannot accept type '{typeof(T)}'.", "color");
										}
										return ToLab(in color9);
									}
									return ToLab(in color8);
								}
								return ToLab(in color7);
							}
							return ToLab(in color6);
						}
						return ToLab(in color5);
					}
					return ToLab(in color4);
				}
				return ToLab(in color3);
			}
			return ToLab(in color2);
		}

		public LChabColor ToLChab(in RGBColor color)
		{
			return ToLChab(ToXYZ(in color));
		}

		public LChabColor ToLChab(in LinearRGBColor color)
		{
			return ToLChab(ToXYZ(in color));
		}

		public LChabColor ToLChab(in XYZColor color)
		{
			return ToLChab(ToLab(in color));
		}

		public LChabColor ToLChab(in xyYColor color)
		{
			return ToLChab(ToXYZ(in color));
		}

		public LChabColor ToLChab(in LabColor color)
		{
			LabColor input = (IsChromaticAdaptationPerformed ? Adapt(in color) : color);
			return LabToLChabConverter.Default.Convert(in input);
		}

		public LChabColor ToLChab(in HunterLabColor color)
		{
			return ToLChab(ToXYZ(in color));
		}

		public LChabColor ToLChab(in LuvColor color)
		{
			return ToLChab(ToXYZ(in color));
		}

		public LChabColor ToLChab(in LChuvColor color)
		{
			return ToLChab(ToXYZ(in color));
		}

		public LChabColor ToLChab(in LMSColor color)
		{
			return ToLChab(ToXYZ(in color));
		}

		public LChabColor ToLChab<T>(T color) where T : struct, IColorVector
		{
			if (!(color is RGBColor color2))
			{
				if (!(color is LinearRGBColor color3))
				{
					if (!(color is XYZColor color4))
					{
						if (!(color is xyYColor color5))
						{
							if (!(color is HunterLabColor color6))
							{
								if (!(color is LabColor color7))
								{
									if (color is LChabColor)
									{
										object obj = color;
										return (LChabColor)((obj is LChabColor) ? obj : null);
									}
									if (!(color is LuvColor color8))
									{
										if (!(color is LChuvColor color9))
										{
											if (color is LMSColor color10)
											{
												return ToLChab(in color10);
											}
											throw new ArgumentException($"Cannot accept type '{typeof(T)}'.", "color");
										}
										return ToLChab(in color9);
									}
									return ToLChab(in color8);
								}
								return ToLChab(in color7);
							}
							return ToLChab(in color6);
						}
						return ToLChab(in color5);
					}
					return ToLChab(in color4);
				}
				return ToLChab(in color3);
			}
			return ToLChab(in color2);
		}

		public LChuvColor ToLChuv(in RGBColor color)
		{
			return ToLChuv(ToXYZ(in color));
		}

		public LChuvColor ToLChuv(in LinearRGBColor color)
		{
			return ToLChuv(ToXYZ(in color));
		}

		public LChuvColor ToLChuv(in XYZColor color)
		{
			return ToLChuv(ToLuv(in color));
		}

		public LChuvColor ToLChuv(in xyYColor color)
		{
			return ToLChuv(ToXYZ(in color));
		}

		public LChuvColor ToLChuv(in LabColor color)
		{
			return ToLChuv(ToXYZ(in color));
		}

		public LChuvColor ToLChuv(in LChabColor color)
		{
			return ToLChuv(ToXYZ(in color));
		}

		public LChuvColor ToLChuv(in HunterLabColor color)
		{
			return ToLChuv(ToXYZ(in color));
		}

		public LChuvColor ToLChuv(in LuvColor color)
		{
			LuvColor input = (IsChromaticAdaptationPerformed ? Adapt(in color) : color);
			return LuvToLChuvConverter.Default.Convert(in input);
		}

		public LChuvColor ToLChuv(in LMSColor color)
		{
			return ToLChuv(ToXYZ(in color));
		}

		public LChuvColor ToLChuv<T>(T color) where T : IColorVector
		{
			if (!(color is RGBColor color2))
			{
				if (!(color is LinearRGBColor color3))
				{
					if (!(color is XYZColor color4))
					{
						if (!(color is xyYColor color5))
						{
							if (!(color is HunterLabColor color6))
							{
								if (!(color is LabColor color7))
								{
									if (!(color is LChabColor color8))
									{
										if (!(color is LuvColor color9))
										{
											if (color is LChuvColor)
											{
												object obj = color;
												return (LChuvColor)((obj is LChuvColor) ? obj : null);
											}
											if (color is LMSColor color10)
											{
												return ToLChuv(in color10);
											}
											throw new ArgumentException($"Cannot accept type '{typeof(T)}'.", "color");
										}
										return ToLChuv(in color9);
									}
									return ToLChuv(in color8);
								}
								return ToLChuv(in color7);
							}
							return ToLChuv(in color6);
						}
						return ToLChuv(in color5);
					}
					return ToLChuv(in color4);
				}
				return ToLChuv(in color3);
			}
			return ToLChuv(in color2);
		}

		public LinearRGBColor ToLinearRGB(in RGBColor color)
		{
			return RGBToLinearRGBConverter.Default.Convert(in color);
		}

		public LinearRGBColor ToLinearRGB(in XYZColor color)
		{
			XYZColor input = ((TargetRGBWorkingSpace.WhitePoint.Equals(WhitePoint) || !IsChromaticAdaptationPerformed) ? color : ChromaticAdaptation.Transform(in color, WhitePoint, TargetRGBWorkingSpace.WhitePoint));
			return GetXYZToLinearRGBConverter(TargetRGBWorkingSpace).Convert(in input);
		}

		public LinearRGBColor ToLinearRGB(in xyYColor color)
		{
			return ToLinearRGB(ToXYZ(in color));
		}

		public LinearRGBColor ToLinearRGB(in LabColor color)
		{
			return ToLinearRGB(ToXYZ(in color));
		}

		public LinearRGBColor ToLinearRGB(in LChabColor color)
		{
			return ToLinearRGB(ToXYZ(in color));
		}

		public LinearRGBColor ToLinearRGB(in HunterLabColor color)
		{
			return ToLinearRGB(ToXYZ(in color));
		}

		public LinearRGBColor ToLinearRGB(in LuvColor color)
		{
			return ToLinearRGB(ToXYZ(in color));
		}

		public LinearRGBColor ToLinearRGB(in LChuvColor color)
		{
			return ToLinearRGB(ToXYZ(in color));
		}

		public LinearRGBColor ToLinearRGB(in LMSColor color)
		{
			return ToLinearRGB(ToXYZ(in color));
		}

		public LinearRGBColor ToLinearRGB<T>(T color) where T : IColorVector
		{
			if (!(color is RGBColor color2))
			{
				if (color is LinearRGBColor)
				{
					object obj = color;
					return (LinearRGBColor)((obj is LinearRGBColor) ? obj : null);
				}
				if (!(color is XYZColor color3))
				{
					if (!(color is xyYColor color4))
					{
						if (!(color is HunterLabColor color5))
						{
							if (!(color is LabColor color6))
							{
								if (!(color is LChabColor color7))
								{
									if (!(color is LuvColor color8))
									{
										if (!(color is LChuvColor color9))
										{
											if (color is LMSColor color10)
											{
												return ToLinearRGB(in color10);
											}
											throw new ArgumentException($"Cannot accept type '{typeof(T)}'.", "color");
										}
										return ToLinearRGB(in color9);
									}
									return ToLinearRGB(in color8);
								}
								return ToLinearRGB(in color7);
							}
							return ToLinearRGB(in color6);
						}
						return ToLinearRGB(in color5);
					}
					return ToLinearRGB(in color4);
				}
				return ToLinearRGB(in color3);
			}
			return ToLinearRGB(in color2);
		}

		public LMSColor ToLMS(in RGBColor color)
		{
			return ToLMS(ToXYZ(in color));
		}

		public LMSColor ToLMS(in LinearRGBColor color)
		{
			return ToLMS(ToXYZ(in color));
		}

		public LMSColor ToLMS(in XYZColor color)
		{
			return _cachedXYZAndLMSConverter.Convert(in color);
		}

		public LMSColor ToLMS(in xyYColor color)
		{
			return ToLMS(ToXYZ(in color));
		}

		public LMSColor ToLMS(in LabColor color)
		{
			return ToLMS(ToXYZ(in color));
		}

		public LMSColor ToLMS(in LChabColor color)
		{
			return ToLMS(ToXYZ(in color));
		}

		public LMSColor ToLMS(in HunterLabColor color)
		{
			return ToLMS(ToXYZ(in color));
		}

		public LMSColor ToLMS(in LuvColor color)
		{
			return ToLMS(ToXYZ(in color));
		}

		public LMSColor ToLMS(in LChuvColor color)
		{
			return ToLMS(ToXYZ(in color));
		}

		public LMSColor ToLMS<T>(T color) where T : IColorVector
		{
			if (!(color is RGBColor color2))
			{
				if (!(color is LinearRGBColor color3))
				{
					if (!(color is XYZColor color4))
					{
						if (!(color is xyYColor color5))
						{
							if (!(color is HunterLabColor color6))
							{
								if (!(color is LabColor color7))
								{
									if (!(color is LChabColor color8))
									{
										if (!(color is LuvColor color9))
										{
											if (!(color is LChuvColor color10))
											{
												if (color is LMSColor)
												{
													object obj = color;
													return (LMSColor)((obj is LMSColor) ? obj : null);
												}
												throw new ArgumentException($"Cannot accept type '{typeof(T)}'.", "color");
											}
											return ToLMS(in color10);
										}
										return ToLMS(in color9);
									}
									return ToLMS(in color8);
								}
								return ToLMS(in color7);
							}
							return ToLMS(in color6);
						}
						return ToLMS(in color5);
					}
					return ToLMS(in color4);
				}
				return ToLMS(in color3);
			}
			return ToLMS(in color2);
		}

		public LuvColor ToLuv(in RGBColor color)
		{
			return ToLuv(ToXYZ(in color));
		}

		public LuvColor ToLuv(in LinearRGBColor color)
		{
			return ToLuv(ToXYZ(in color));
		}

		public LuvColor ToLuv(in XYZColor color)
		{
			XYZColor input = ((!WhitePoint.Equals(TargetLuvWhitePoint) && IsChromaticAdaptationPerformed) ? ChromaticAdaptation.Transform(in color, WhitePoint, TargetLuvWhitePoint) : color);
			return new XYZToLuvConverter(TargetLuvWhitePoint).Convert(in input);
		}

		public LuvColor ToLuv(in xyYColor color)
		{
			return ToLuv(ToXYZ(in color));
		}

		public LuvColor ToLuv(in LabColor color)
		{
			return ToLuv(ToXYZ(in color));
		}

		public LuvColor ToLuv(in LChabColor color)
		{
			return ToLuv(ToXYZ(in color));
		}

		public LuvColor ToLuv(in HunterLabColor color)
		{
			return ToLuv(ToXYZ(in color));
		}

		public LuvColor ToLuv(in LChuvColor color)
		{
			LuvColor color2 = LChuvToLuvConverter.Default.Convert(in color);
			if (!IsChromaticAdaptationPerformed)
			{
				return color2;
			}
			return Adapt(in color2);
		}

		public LuvColor ToLuv(in LMSColor color)
		{
			return ToLuv(ToXYZ(in color));
		}

		public LuvColor ToLuv<T>(T color) where T : IColorVector
		{
			if (!(color is RGBColor color2))
			{
				if (!(color is LinearRGBColor color3))
				{
					if (!(color is XYZColor color4))
					{
						if (!(color is xyYColor color5))
						{
							if (!(color is HunterLabColor color6))
							{
								if (!(color is LabColor color7))
								{
									if (!(color is LChabColor color8))
									{
										if (color is LuvColor)
										{
											object obj = color;
											return (LuvColor)((obj is LuvColor) ? obj : null);
										}
										if (!(color is LChuvColor color9))
										{
											if (color is LMSColor color10)
											{
												return ToLuv(in color10);
											}
											throw new ArgumentException($"Cannot accept type '{typeof(T)}'.", "color");
										}
										return ToLuv(in color9);
									}
									return ToLuv(in color8);
								}
								return ToLuv(in color7);
							}
							return ToLuv(in color6);
						}
						return ToLuv(in color5);
					}
					return ToLuv(in color4);
				}
				return ToLuv(in color3);
			}
			return ToLuv(in color2);
		}

		private XYZToLinearRGBConverter GetXYZToLinearRGBConverter(IRGBWorkingSpace workingSpace)
		{
			if (_lastXYZToLinearRGBConverter != null && _lastXYZToLinearRGBConverter.TargetRGBWorkingSpace.Equals(workingSpace))
			{
				return _lastXYZToLinearRGBConverter;
			}
			return _lastXYZToLinearRGBConverter = new XYZToLinearRGBConverter(workingSpace);
		}

		public RGBColor ToRGB(in LinearRGBColor color)
		{
			return LinearRGBToRGBConverter.Default.Convert(in color);
		}

		public RGBColor ToRGB(in XYZColor color)
		{
			return ToRGB(ToLinearRGB(in color));
		}

		public RGBColor ToRGB(in xyYColor color)
		{
			return ToRGB(ToXYZ(in color));
		}

		public RGBColor ToRGB(in LabColor color)
		{
			return ToRGB(ToXYZ(in color));
		}

		public RGBColor ToRGB(in LChabColor color)
		{
			return ToRGB(ToXYZ(in color));
		}

		public RGBColor ToRGB(in HunterLabColor color)
		{
			return ToRGB(ToXYZ(in color));
		}

		public RGBColor ToRGB(in LuvColor color)
		{
			return ToRGB(ToXYZ(in color));
		}

		public RGBColor ToRGB(in LChuvColor color)
		{
			return ToRGB(ToXYZ(in color));
		}

		public RGBColor ToRGB(in LMSColor color)
		{
			return ToRGB(ToXYZ(in color));
		}

		public RGBColor ToRGB<T>(T color) where T : IColorVector
		{
			if (color is RGBColor)
			{
				object obj = color;
				return (RGBColor)((obj is RGBColor) ? obj : null);
			}
			if (!(color is LinearRGBColor color2))
			{
				if (!(color is XYZColor color3))
				{
					if (!(color is xyYColor color4))
					{
						if (!(color is HunterLabColor color5))
						{
							if (!(color is LabColor color6))
							{
								if (!(color is LChabColor color7))
								{
									if (!(color is LuvColor color8))
									{
										if (!(color is LChuvColor color9))
										{
											if (color is LMSColor color10)
											{
												return ToRGB(in color10);
											}
											throw new ArgumentException($"Cannot accept type '{typeof(T)}'.", "color");
										}
										return ToRGB(in color9);
									}
									return ToRGB(in color8);
								}
								return ToRGB(in color7);
							}
							return ToRGB(in color6);
						}
						return ToRGB(in color5);
					}
					return ToRGB(in color4);
				}
				return ToRGB(in color3);
			}
			return ToRGB(in color2);
		}

		public xyYColor ToxyY(in RGBColor color)
		{
			return ToxyY(ToXYZ(in color));
		}

		public xyYColor ToxyY(in LinearRGBColor color)
		{
			return ToxyY(ToXYZ(in color));
		}

		public xyYColor ToxyY(in XYZColor color)
		{
			return new xyYAndXYZConverter().Convert(in color);
		}

		public xyYColor ToxyY(in LabColor color)
		{
			return ToxyY(ToXYZ(in color));
		}

		public xyYColor ToxyY(in LChabColor color)
		{
			return ToxyY(ToXYZ(in color));
		}

		public xyYColor ToxyY(in HunterLabColor color)
		{
			return ToxyY(ToXYZ(in color));
		}

		public xyYColor ToxyY(in LuvColor color)
		{
			return ToxyY(ToXYZ(in color));
		}

		public xyYColor ToxyY(in LChuvColor color)
		{
			return ToxyY(ToXYZ(in color));
		}

		public xyYColor ToxyY(in LMSColor color)
		{
			return ToxyY(ToXYZ(in color));
		}

		public xyYColor ToxyY<T>(T color) where T : IColorVector
		{
			if (!(color is RGBColor color2))
			{
				if (!(color is LinearRGBColor color3))
				{
					if (!(color is XYZColor color4))
					{
						if (color is xyYColor)
						{
							object obj = color;
							return (xyYColor)((obj is xyYColor) ? obj : null);
						}
						if (!(color is HunterLabColor color5))
						{
							if (!(color is LabColor color6))
							{
								if (!(color is LChabColor color7))
								{
									if (!(color is LuvColor color8))
									{
										if (!(color is LChuvColor color9))
										{
											if (color is LMSColor color10)
											{
												return ToxyY(in color10);
											}
											throw new ArgumentException($"Cannot accept type '{typeof(T)}'.", "color");
										}
										return ToxyY(in color9);
									}
									return ToxyY(in color8);
								}
								return ToxyY(in color7);
							}
							return ToxyY(in color6);
						}
						return ToxyY(in color5);
					}
					return ToxyY(in color4);
				}
				return ToxyY(in color3);
			}
			return ToxyY(in color2);
		}

		private LinearRGBToXYZConverter GetLinearRGBToXYZConverter(IRGBWorkingSpace workingSpace)
		{
			if (_lastLinearRGBToXYZConverter != null && _lastLinearRGBToXYZConverter.SourceRGBWorkingSpace.Equals(workingSpace))
			{
				return _lastLinearRGBToXYZConverter;
			}
			return _lastLinearRGBToXYZConverter = new LinearRGBToXYZConverter(workingSpace);
		}

		public XYZColor ToXYZ(in RGBColor color)
		{
			return ToXYZ(RGBToLinearRGBConverter.Default.Convert(in color));
		}

		public XYZColor ToXYZ(in LinearRGBColor color)
		{
			XYZColor color2 = GetLinearRGBToXYZConverter(color.WorkingSpace).Convert(in color);
			if (!color.WorkingSpace.WhitePoint.Equals(WhitePoint) && IsChromaticAdaptationPerformed)
			{
				return Adapt(in color2, color.WorkingSpace.WhitePoint);
			}
			return color2;
		}

		public XYZColor ToXYZ(in xyYColor color)
		{
			return xyYAndXYZConverter.Default.Convert(in color);
		}

		public XYZColor ToXYZ(in LabColor color)
		{
			XYZColor color2 = LabToXYZConverter.Default.Convert(in color);
			if (!color.WhitePoint.Equals(WhitePoint) && IsChromaticAdaptationPerformed)
			{
				return Adapt(in color2, color.WhitePoint);
			}
			return color2;
		}

		public XYZColor ToXYZ(in LChabColor color)
		{
			return ToXYZ(LChabToLabConverter.Default.Convert(in color));
		}

		public XYZColor ToXYZ(in HunterLabColor color)
		{
			XYZColor color2 = HunterLabToXYZConverter.Default.Convert(in color);
			if (!color.WhitePoint.Equals(WhitePoint) && IsChromaticAdaptationPerformed)
			{
				return Adapt(in color2, color.WhitePoint);
			}
			return color2;
		}

		public XYZColor ToXYZ(in LuvColor color)
		{
			XYZColor color2 = LuvToXYZConverter.Default.Convert(in color);
			if (!color.WhitePoint.Equals(WhitePoint) && IsChromaticAdaptationPerformed)
			{
				return Adapt(in color2, color.WhitePoint);
			}
			return color2;
		}

		public XYZColor ToXYZ(in LChuvColor color)
		{
			return ToXYZ(LChuvToLuvConverter.Default.Convert(in color));
		}

		public XYZColor ToXYZ(in LMSColor color)
		{
			return _cachedXYZAndLMSConverter.Convert(in color);
		}

		public XYZColor ToXYZ<T>(T color) where T : IColorVector
		{
			if (!(color is RGBColor color2))
			{
				if (!(color is LinearRGBColor color3))
				{
					if (color is XYZColor)
					{
						object obj = color;
						return (XYZColor)((obj is XYZColor) ? obj : null);
					}
					if (!(color is xyYColor color4))
					{
						if (!(color is HunterLabColor color5))
						{
							if (!(color is LabColor color6))
							{
								if (!(color is LChabColor color7))
								{
									if (!(color is LuvColor color8))
									{
										if (!(color is LChuvColor color9))
										{
											if (color is LMSColor color10)
											{
												return ToXYZ(in color10);
											}
											throw new ArgumentException($"Cannot accept type '{typeof(T)}'.", "color");
										}
										return ToXYZ(in color9);
									}
									return ToXYZ(in color8);
								}
								return ToXYZ(in color7);
							}
							return ToXYZ(in color6);
						}
						return ToXYZ(in color5);
					}
					return ToXYZ(in color4);
				}
				return ToXYZ(in color3);
			}
			return ToXYZ(in color2);
		}
	}
	public interface IChromaticAdaptation
	{
		XYZColor Transform(in XYZColor sourceColor, in XYZColor sourceWhitePoint, in XYZColor targetWhitePoint);
	}
	public sealed class VonKriesChromaticAdaptation : IChromaticAdaptation
	{
		private readonly IColorConversion<XYZColor, LMSColor> _conversionToLMS;

		private readonly IColorConversion<LMSColor, XYZColor> _conversionToXYZ;

		private IReadOnlyList<IReadOnlyList<double>> _cachedDiagonalMatrix;

		private XYZColor _lastSourceWhitePoint;

		private XYZColor _lastTargetWhitePoint;

		public VonKriesChromaticAdaptation()
			: this(new XYZAndLMSConverter())
		{
		}

		public VonKriesChromaticAdaptation(IReadOnlyList<IReadOnlyList<double>> transformationMatrix)
			: this(new XYZAndLMSConverter(transformationMatrix))
		{
		}

		private VonKriesChromaticAdaptation(XYZAndLMSConverter converter)
			: this(converter, converter)
		{
		}

		public VonKriesChromaticAdaptation(IColorConversion<XYZColor, LMSColor> conversionToLMS, IColorConversion<LMSColor, XYZColor> conversionToXYZ)
		{
			_conversionToLMS = conversionToLMS ?? throw new ArgumentNullException("conversionToLMS");
			_conversionToXYZ = conversionToXYZ ?? throw new ArgumentNullException("conversionToXYZ");
		}

		public XYZColor Transform(in XYZColor sourceColor, in XYZColor sourceWhitePoint, in XYZColor targetWhitePoint)
		{
			if (sourceWhitePoint.Equals(targetWhitePoint))
			{
				return sourceColor;
			}
			LMSColor lMSColor = _conversionToLMS.Convert(in sourceColor);
			if (sourceWhitePoint != _lastSourceWhitePoint || targetWhitePoint != _lastTargetWhitePoint)
			{
				LMSColor lMSColor2 = _conversionToLMS.Convert(in sourceWhitePoint);
				LMSColor lMSColor3 = _conversionToLMS.Convert(in targetWhitePoint);
				_cachedDiagonalMatrix = MatrixFactory.CreateDiagonal(lMSColor3.L / lMSColor2.L, lMSColor3.M / lMSColor2.M, lMSColor3.S / lMSColor2.S);
				_lastSourceWhitePoint = sourceWhitePoint;
				_lastTargetWhitePoint = targetWhitePoint;
			}
			LMSColor input = new LMSColor(_cachedDiagonalMatrix.MultiplyBy(lMSColor.Vector));
			return _conversionToXYZ.Convert(in input);
		}

		XYZColor IChromaticAdaptation.Transform(in XYZColor sourceColor, in XYZColor sourceWhitePoint, in XYZColor targetWhitePoint)
		{
			return Transform(in sourceColor, in sourceWhitePoint, in targetWhitePoint);
		}
	}
}
