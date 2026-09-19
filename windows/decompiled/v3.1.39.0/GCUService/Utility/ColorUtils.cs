using System;
using System.Drawing;

namespace Utility;

internal class ColorUtils
{
	public static Color BlendColors(Color background, Color foreground, double percent)
	{
		if (percent < 0.0)
		{
			percent = 0.0;
		}
		else if (percent > 1.0)
		{
			percent = 1.0;
		}
		int red = (byte)Math.Min((double)(int)foreground.R * percent + (double)(int)background.R * (1.0 - percent), 255.0);
		int green = (byte)Math.Min((double)(int)foreground.G * percent + (double)(int)background.G * (1.0 - percent), 255.0);
		int blue = (byte)Math.Min((double)(int)foreground.B * percent + (double)(int)background.B * (1.0 - percent), 255.0);
		return Color.FromArgb((byte)Math.Min((double)(int)foreground.A * percent + (double)(int)background.A * (1.0 - percent), 255.0), red, green, blue);
	}
}
