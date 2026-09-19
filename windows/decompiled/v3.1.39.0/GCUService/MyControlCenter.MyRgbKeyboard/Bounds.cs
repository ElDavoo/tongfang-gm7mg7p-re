using System;

namespace MyControlCenter.MyRgbKeyboard;

public struct Bounds
{
	public int Left;

	public int Top;

	public int Right;

	public int Bottom;

	public Bounds(int iX = 0, int iY = 0, int iWidth = 0, int iHeight = 0)
	{
		Left = iX;
		Top = iY;
		Right = iX + iWidth;
		Bottom = iY + iHeight;
	}

	public Bounds(Bounds Other)
	{
		Left = Other.Left;
		Top = Other.Top;
		Right = Other.Right;
		Bottom = Other.Bottom;
	}

	public void SetBounds(int iX, int iY, int iWidth = 0, int iHeight = 0)
	{
		Left = iX;
		Top = iY;
		Right = iX + iWidth;
		Bottom = iY + iHeight;
	}

	public void SetBounds(Bounds Other)
	{
		Left = Other.Left;
		Top = Other.Top;
		Right = Other.Right;
		Bottom = Other.Bottom;
	}

	public void MoveRight(int iDistance)
	{
		Left += iDistance;
		Right += iDistance;
	}

	public void Move(int Direction)
	{
		Left += Direction;
		Right += Direction;
	}

	public void MoveDown(int iDistance)
	{
		Top += iDistance;
		Bottom += iDistance;
	}

	public void Move(vector2D iVector, int iSpeed)
	{
		Left += (int)Math.Ceiling(iVector.X * (double)iSpeed);
		Right += (int)Math.Ceiling(iVector.X * (double)iSpeed);
		Top += (int)Math.Ceiling(iVector.Y * (double)iSpeed);
		Bottom += (int)Math.Ceiling(iVector.Y * (double)iSpeed);
	}
}
