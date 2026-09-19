using System;

namespace MyControlCenter.MyRgbKeyboard;

public struct vector2D
{
	private double x;

	private double y;

	public double X => x;

	public double Y => y;

	public void NegateX()
	{
		x = 0.0 - x;
	}

	public void NegateY()
	{
		y = 0.0 - y;
	}

	public vector2D(double iX, double iY)
	{
		double num = Math.Sqrt(iX * iX + iY * iY);
		x = iX / num;
		y = iY / num;
	}

	public void setValue(double iX, double iY)
	{
		double num = Math.Sqrt(iX * iX + iY * iY);
		x = iX / num;
		y = iY / num;
	}
}
