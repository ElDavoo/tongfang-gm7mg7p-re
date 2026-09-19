using System;
using LightingModel;

namespace MyControlCenter.MyRgbKeyboard;

internal abstract class Actor
{
	internal RGB_S ActorColor;

	internal RGB_S ActorColortemp;

	internal float currentBrightness;

	public int CurrentDirection = 1;

	public Bounds PositionBounds;

	public Bounds CollisionBounds;

	public Bounds MoveBounds;

	public Actor()
	{
	}

	public Actor(int iX, int iY)
	{
		PositionBounds.SetBounds(iX, iY);
		CollisionBounds.SetBounds(iX, iY);
	}

	public abstract void Update();

	public void MoveByDirection()
	{
		PositionBounds.MoveRight(CurrentDirection);
		CollisionBounds.MoveRight(CurrentDirection);
		if ((double)currentBrightness > 0.1)
		{
			if (currentBrightness - 0.45f > 0.1f)
			{
				currentBrightness -= 0.45f;
				setBrightness();
			}
			else
			{
				currentBrightness = 0.1f;
				setBrightness();
			}
		}
		else
		{
			currentBrightness = 0.1f;
			setBrightness();
		}
	}

	private void setBrightness()
	{
		ActorColor.R = Convert.ToByte((float)(int)ActorColortemp.R * currentBrightness);
		ActorColor.G = Convert.ToByte((float)(int)ActorColortemp.G * currentBrightness);
		ActorColor.B = Convert.ToByte((float)(int)ActorColortemp.B * currentBrightness);
	}

	public void setDirection(int direction)
	{
		CurrentDirection = direction;
	}

	public void DirectionReverse()
	{
		CurrentDirection *= -1;
		ActorColor = ActorColortemp;
		currentBrightness = 1f;
	}

	public void MoveRight(int distance)
	{
		PositionBounds.MoveRight(distance);
		CollisionBounds.MoveRight(distance);
	}

	public void MoveDown(int distance)
	{
		PositionBounds.MoveDown(distance);
		CollisionBounds.MoveDown(distance);
	}

	public bool IsCollisionDirectionWith(Actor Other)
	{
		return IsCollision(this, Other);
	}

	public static bool IsCollision(Actor a, Actor b)
	{
		if (a.CollisionBounds.Right < b.CollisionBounds.Left || a.CollisionBounds.Bottom < b.CollisionBounds.Top || b.CollisionBounds.Right < a.CollisionBounds.Left || b.CollisionBounds.Bottom < a.CollisionBounds.Top)
		{
			return false;
		}
		if (CheckColor(a) && CheckColor(b))
		{
			return true;
		}
		return false;
	}

	public static bool CheckColor(Actor actitem)
	{
		if (actitem.ActorColor.R == 0 && actitem.ActorColor.G == 0 && actitem.ActorColor.B == 0)
		{
			return false;
		}
		return true;
	}
}
