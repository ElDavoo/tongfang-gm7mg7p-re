using System.Collections.Generic;
using System.Windows.Media;
using LightingModel;

namespace MyControlCenter.MyRgbKeyboard;

internal class _2p2ndkeyboard : HIDKeyboard
{
	public _2p2ndkeyboard(LM_Manager lm_Manger, string fwVersion)
		: base(lm_Manger, fwVersion)
	{
		_KeyboardControl.ColShift = 0;
		_KeyboardControl.ColRightShift = 1;
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
		if (_EffectData.save_effect == 5)
		{
			List<Color> obj = new List<Color>
			{
				Color.FromArgb(byte.MaxValue, byte.MaxValue, 0, 0),
				Color.FromArgb(byte.MaxValue, byte.MaxValue, 165, 0),
				Color.FromArgb(byte.MaxValue, byte.MaxValue, byte.MaxValue, 0),
				Color.FromArgb(byte.MaxValue, 0, byte.MaxValue, 0),
				Color.FromArgb(byte.MaxValue, 0, byte.MaxValue, byte.MaxValue),
				Color.FromArgb(byte.MaxValue, 0, 0, byte.MaxValue),
				Color.FromArgb(byte.MaxValue, 139, 0, byte.MaxValue)
			};
			RGBKB_Color save_layout_color = new RGBKB_Color(bCircular: false, 7u)
			{
				isCircular = true
			};
			int num = 0;
			foreach (Color item in obj)
			{
				save_layout_color.ColorBuffer[num].ID = (uint)num;
				save_layout_color.ColorBuffer[num].R = item.R;
				save_layout_color.ColorBuffer[num].G = item.G;
				save_layout_color.ColorBuffer[num].B = item.B;
				num++;
			}
			_EffectData.save_layout_color = save_layout_color;
		}
		base.RunEffct(saved);
	}
}
