using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows.Media;
using LightingModel;
using Utility;

namespace MyControlCenter.MyRgbKeyboard;

internal class HIDLightbar2 : HIDKeyboard
{
	private byte HIDRGBLIGHBAR_EFFECT_Colorwave = 32;

	private byte HIDRGBLIGHBAR_EFFECT_ColorBreath = 19;

	private byte HIDRGBLIGHBAR_EFFECT_Thinking = 33;

	private const byte EFFECT_STARSPARK = 24;

	private const byte EFFECT_STARHITTING = 25;

	private const byte EFFECT_BATTERYPRECENT = 35;

	private SAVE_LIGHTING_EFFECT_DATA beforeEffect;

	public HIDLightbar2(LM_Manager lm_Manger, string fwVersion)
		: base(lm_Manger, fwVersion)
	{
		SetACDCLightString("LightbarPowerSwitch", "LightbarACLight", "LightbarDCLight");
		_KeyboardControl.ColShift = 0;
		_KeyboardControl.ColRightShift = 1;
	}

	internal override void PluggedSetBrightness(uint brigtness)
	{
		base.PluggedSetBrightness(brigtness);
	}

	public override void AsyncWelcome()
	{
		try
		{
			List<string[]> lightbarWelcomeEffect = NvramVariable.GetLightbarWelcomeEffect();
			LogCtrl.TraceMessage("data[0]: " + string.Join(",", lightbarWelcomeEffect[0]), "AsyncWelcome", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\HIDLightbar2.cs", 59);
			LogCtrl.TraceMessage("data[1]: " + string.Join(",", lightbarWelcomeEffect[1]), "AsyncWelcome", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\HIDLightbar2.cs", 60);
			SAVE_LIGHTING_EFFECT_DATA welcomeEffectData = default(SAVE_LIGHTING_EFFECT_DATA);
			RGBKB_PowerStatus rGBKB_PowerStatus = RGBKB_PowerStatus.On;
			if (Convert.ToByte(lightbarWelcomeEffect[0][0]) != byte.MaxValue)
			{
				welcomeEffectData.save_effect = Convert.ToByte(Convert.ToUInt32(lightbarWelcomeEffect[0][2], 16));
				welcomeEffectData.save_speed = Convert.ToByte(Convert.ToUInt32(lightbarWelcomeEffect[0][3], 16));
				welcomeEffectData.save_light = Convert.ToByte(Convert.ToUInt32(lightbarWelcomeEffect[0][4], 16));
				welcomeEffectData.save_direction = Convert.ToByte(Convert.ToUInt32(lightbarWelcomeEffect[0][5], 16));
				rGBKB_PowerStatus = (Convert.ToBoolean(Convert.ToUInt32(lightbarWelcomeEffect[1][2], 16)) ? RGBKB_PowerStatus.On : RGBKB_PowerStatus.Off);
				_WelcomeEffectData = welcomeEffectData;
				SetPowerStatus(rGBKB_PowerStatus);
			}
		}
		catch (Exception)
		{
		}
	}

	public override void SetBrinessByScanCode(int scancode)
	{
		if (scancode == 175)
		{
			LogCtrl.Write("HIDLighbar2 : scan code: " + scancode);
			if (_PowerStatus.Equals(RGBKB_PowerStatus.Off))
			{
				_PowerStatus = RGBKB_PowerStatus.On;
				SavePowerStatus();
				RunEffct(0);
			}
			else
			{
				_PowerStatus = RGBKB_PowerStatus.Off;
				SavePowerStatus();
			}
		}
	}

	public override uint GetBrightness()
	{
		return base.GetBrightness();
	}

	public override void RunWelcomeEffect()
	{
		if (_WelcomeEffectData.save_effect == 3 || _WelcomeEffectData.save_effect == HIDRGBLIGHBAR_EFFECT_Colorwave)
		{
			_WelcomeEffectData.save_effect = HIDRGBLIGHBAR_EFFECT_Colorwave;
			base.RunWelcomeEffect();
		}
		else
		{
			base.RunWelcomeEffect();
		}
	}

	public override void RunEffct(byte saved)
	{
		if (_EffectData.save_effect == 1)
		{
			List<RGB_S> list = new List<RGB_S>();
			for (int i = 0; i < _EffectData.save_layout_color.ColorBuffer.Count(); i++)
			{
				RGB_S rGB_S = _EffectData.save_layout_color.ColorBuffer[0];
				list.Add(new RGB_S((uint)i, rGB_S.R, rGB_S.G, rGB_S.B));
			}
			_EffectData.save_layout_color.ColorBuffer = list.ToArray();
			base.RunEffct(saved);
		}
		else if (_EffectData.save_effect == 5)
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
			base.RunEffct(saved);
		}
		else if (_EffectData.save_effect == 3 || _EffectData.save_effect == HIDRGBLIGHBAR_EFFECT_Colorwave)
		{
			_EffectData.save_effect = HIDRGBLIGHBAR_EFFECT_Colorwave;
			base.RunEffct(saved);
		}
		else if (_EffectData.save_effect == 19)
		{
			base.RunEffct(saved);
		}
		else if (_EffectData.save_effect == 2)
		{
			base.RunEffct(saved);
		}
		else if (_EffectData.save_effect == 51)
		{
			base.RunEffct(saved);
		}
		else if (_EffectData.save_effect == 25)
		{
			_EffectData.save_effect = 51;
			base.RunEffct(saved);
			_EffectData.save_effect = 25;
			base.RunEffct(saved);
		}
		else if (_EffectData.save_effect == 24)
		{
			_EffectData.save_effect = 51;
			base.RunEffct(saved);
			_EffectData.save_effect = 24;
			base.RunEffct(saved);
		}
		else if (_EffectData.save_effect == 35)
		{
			_EffectData.save_effect = 51;
			base.RunEffct(saved);
			_EffectData.save_effect = 35;
			base.RunEffct(saved);
		}
		else
		{
			base.RunEffct(saved);
		}
		beforeEffect = _EffectData;
	}

	private byte AsyncSpeed(byte save_speed)
	{
		return save_speed switch
		{
			1 => 3, 
			3 => 5, 
			5 => 7, 
			7 => 9, 
			10 => save_speed, 
			_ => save_speed, 
		};
	}
}
