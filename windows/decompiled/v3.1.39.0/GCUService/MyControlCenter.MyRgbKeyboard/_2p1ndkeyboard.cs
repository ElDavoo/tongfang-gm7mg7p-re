using LightingModel;

namespace MyControlCenter.MyRgbKeyboard;

internal class _2p1ndkeyboard : HIDKeyboard
{
	public _2p1ndkeyboard(LM_Manager lm_Manger, string fwVersion)
		: base(lm_Manger, fwVersion)
	{
		_KeyboardControl.ColShift = 2;
		_KeyboardControl.ColRightShift = 3;
	}

	internal override void PluggedSetBrightness(uint brigtness)
	{
		base.PluggedSetBrightness(brigtness);
	}

	public override uint GetBrightness()
	{
		return base.GetBrightness();
	}

	public override void RunEffct(byte saved)
	{
		base.RunEffct(saved);
	}
}
