using System.Linq;
using System.Windows.Media;

namespace DynamicDesk;

public static class GradientStopCollectionExtensions
{
	public static Color GetRelativeColor(this GradientStopCollection gsc, double offset)
	{
		GradientStop gradientStop = gsc.SingleOrDefault((GradientStop f) => f.Offset == offset);
		if (gradientStop != null)
		{
			return gradientStop.Color;
		}
		GradientStop gradientStop2 = gsc.Where((GradientStop w) => w.Offset == gsc.Min((GradientStop m) => m.Offset)).First();
		GradientStop gradientStop3 = gsc.Where((GradientStop w) => w.Offset == gsc.Max((GradientStop m) => m.Offset)).First();
		foreach (GradientStop item in gsc)
		{
			if (item.Offset < offset && item.Offset > gradientStop2.Offset)
			{
				gradientStop2 = item;
			}
			if (item.Offset > offset && item.Offset < gradientStop3.Offset)
			{
				gradientStop3 = item;
			}
		}
		return new Color
		{
			ScA = (float)((offset - gradientStop2.Offset) * (double)(gradientStop3.Color.ScA - gradientStop2.Color.ScA) / (gradientStop3.Offset - gradientStop2.Offset) + (double)gradientStop2.Color.ScA),
			ScR = (float)((offset - gradientStop2.Offset) * (double)(gradientStop3.Color.ScR - gradientStop2.Color.ScR) / (gradientStop3.Offset - gradientStop2.Offset) + (double)gradientStop2.Color.ScR),
			ScG = (float)((offset - gradientStop2.Offset) * (double)(gradientStop3.Color.ScG - gradientStop2.Color.ScG) / (gradientStop3.Offset - gradientStop2.Offset) + (double)gradientStop2.Color.ScG),
			ScB = (float)((offset - gradientStop2.Offset) * (double)(gradientStop3.Color.ScB - gradientStop2.Color.ScB) / (gradientStop3.Offset - gradientStop2.Offset) + (double)gradientStop2.Color.ScB)
		};
	}
}
