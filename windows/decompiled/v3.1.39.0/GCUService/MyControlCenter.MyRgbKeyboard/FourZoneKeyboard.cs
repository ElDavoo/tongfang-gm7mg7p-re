using System.Collections.Generic;
using System.Windows.Media;
using LightingModel;
using Utility;

namespace MyControlCenter.MyRgbKeyboard;

internal class FourZoneKeyboard : HIDKeyboard
{
	public FourZoneKeyboard(LM_Manager lm_Manger, string fwVersion)
		: base(lm_Manger, fwVersion)
	{
	}

	public override void SetBrinessByScanCode(int scancode)
	{
		if (scancode != 177 && scancode != 178)
		{
			return;
		}
		LogCtrl.Write("HID_Default B1 B2 : scan code: " + scancode);
		if (_PowerStatus.Equals(RGBKB_PowerStatus.Off))
		{
			_PowerStatus = RGBKB_PowerStatus.On;
			SavePowerStatus();
			RunEffct(0);
		}
		uint num = Translate_Layout_LightValue(_EffectData.save_light);
		bool flag = true;
		switch (scancode)
		{
		case 177:
			num = ((num != 0) ? (num - 1) : 0u);
			break;
		case 178:
			if (num + 1 > 4)
			{
				num = 4u;
				flag = false;
			}
			else
			{
				num++;
			}
			break;
		}
		_EffectData.save_light = Translate_ITE_LightValue(num);
		if (flag)
		{
			SetBrightnessStrategy(_EffectData.save_light);
		}
		RGBKB_Event_Data event_data = new RGBKB_Event_Data
		{
			event_id = RGBKB_EventID.Brightness_update,
			envet_data_len = 1u,
			event_data = new byte[1]
		};
		event_data.event_data[0] = (byte)Translate_Layout_LightValue(_EffectData.save_light);
		ScanCodeUpdatedBrightness(event_data);
	}

	internal override void SetBrightnessStrategy(byte brightness, bool saveACDC = true)
	{
		if (brightness == 0)
		{
			LM_ITE_RGB keyboardControl = _KeyboardControl;
			if (keyboardControl != null && keyboardControl.ILM_RGBKB_GetRGBKeyboardType() == RGBKB_Type.FourZone && _EffectData.save_effect == 34)
			{
				_KeyboardControl?.StopMusicTransfer();
			}
		}
		if (saveACDC)
		{
			if (CurrentPowerMode == RGBKB_PowerMode.DC)
			{
				_DC_LightLevel = Translate_Layout_LightValue(brightness);
			}
			else
			{
				_AC_LightLevel = Translate_Layout_LightValue(brightness);
			}
		}
		if (_KeyboardControl.Ver_High >= 17 && _KeyboardControl.Ver_Low >= 3)
		{
			LogCtrl.Write("Fourzone in scancode support 09h : " + _EffectData.save_light);
			_KeyboardControl.HID_Set_Brightness_Level_09H(brightness);
		}
		else
		{
			_KeyboardControl.Set_Lighting_Effect(2, _EffectData.save_effect, brightness, _EffectData.save_speed, _EffectData.save_direction, 0, _EffectData.save_layout_color);
			LogCtrl.Write("FourZone FW < 0x03");
		}
		if (saveACDC)
		{
			SaveEffectData();
		}
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
				Color.FromArgb(byte.MaxValue, 0, byte.MaxValue, 0),
				Color.FromArgb(byte.MaxValue, 0, 0, byte.MaxValue),
				Color.FromArgb(byte.MaxValue, 139, 0, byte.MaxValue)
			};
			RGBKB_Color save_layout_color = new RGBKB_Color(bCircular: false, 4u);
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
