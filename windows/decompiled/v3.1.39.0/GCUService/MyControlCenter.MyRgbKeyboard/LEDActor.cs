using LightingModel;

namespace MyControlCenter.MyRgbKeyboard;

internal class LEDActor : Actor
{
	public string ActorName = "";

	public LEDActor(int iX, int iY)
	{
		PositionBounds.SetBounds(iX, iY);
		CollisionBounds.SetBounds(iX, iY);
	}

	public void SetColor(RGB_S color)
	{
		ActorColor = color;
		ActorColortemp = color;
	}

	public override void Update()
	{
	}
}
