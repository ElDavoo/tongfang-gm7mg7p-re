using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using LightingModel;
using Utility;

namespace MyControlCenter.MyRgbKeyboard;

internal class _2p1ndKeyboard_QC : HIDKeyboard
{
	public _2p1ndKeyboard_QC(LM_Manager lm_Manger, string fwVersion)
		: base(lm_Manger, fwVersion)
	{
		_KeyboardControl.ColShift = 2;
		_KeyboardControl.ColRightShift = 3;
	}

	internal override void PluggedSetBrightness(uint brigtness)
	{
		base.PluggedSetBrightness(brigtness);
	}

	internal override byte Translate_ITE_LightValue(uint layoutLight)
	{
		return layoutLight switch
		{
			0u => 0, 
			1u => 8, 
			2u => 22, 
			3u => 36, 
			4u => 50, 
			_ => 0, 
		};
	}

	public override void SetBrightness_ACDC(uint ACBrightness, uint DCBrighteness, bool saveACDC = true)
	{
		if (saveACDC)
		{
			_AC_LightLevel = Convert.ToUInt32(ACBrightness);
			_DC_LightLevel = Convert.ToUInt32(DCBrighteness);
			SettingsStorageExtensions.SaveAsync("", _SaveDCLight, _DC_LightLevel);
			SettingsStorageExtensions.SaveAsync("", _SaveACLight, _AC_LightLevel);
		}
		if (CurrentPowerMode == RGBKB_PowerMode.DC)
		{
			SetBrightnessStrategy(Convert.ToByte(DCBrighteness));
		}
		else
		{
			SetBrightnessStrategy(Convert.ToByte(ACBrightness));
		}
	}

	internal override uint Translate_Layout_LightValue(byte ite_light)
	{
		return ite_light switch
		{
			0 => 0u, 
			8 => 1u, 
			22 => 2u, 
			36 => 3u, 
			50 => 4u, 
			_ => 0u, 
		};
	}

	public override void AsyncWelcome()
	{
	}

	public override bool SetEffect(dynamic data)
	{
		RGBKB_Mode save_mode = data["mode"];
		RGBKB_Effect layoutEffect = data["effect"];
		uint layoutLight = data["light"];
		uint layoutSpeed = data["speed"];
		RGBKB_Direction layoutDirection = data["direction"];
		RGBKB_Color save_layout_color = ConvertJsonRGB2RGBColor(data["color"]);
		RGBKB_NV_SAVE rGBKB_NV_SAVE = data["nv_save"];
		int save_layout_backgroundcolor = 0;
		string save_layout_alphbet = "";
		if (data["backgroundcolor"] != null)
		{
			save_layout_backgroundcolor = Convert.ToInt32(data["backgroundcolor"]);
		}
		if (layoutEffect.Equals(RGBKB_Effect.Alphabet) && data["alphabet"] != null)
		{
			save_layout_alphbet = data["alphabet"];
		}
		SAVE_LIGHTING_EFFECT_DATA sAVE_LIGHTING_EFFECT_DATA = new SAVE_LIGHTING_EFFECT_DATA
		{
			save_mode = save_mode,
			save_effect = Translate_ITE_EffectIndex(layoutEffect),
			save_light = Translate_ITE_LightValue(layoutLight),
			save_speed = Translate_ITE_SpeedValue(layoutSpeed),
			save_direction = Translate_ITE_DirectionValue(layoutDirection),
			save_layout_color = save_layout_color,
			bSaved = Convert.ToBoolean((byte)rGBKB_NV_SAVE),
			save_layout_alphbet = save_layout_alphbet,
			save_layout_backgroundcolor = save_layout_backgroundcolor
		};
		if (_EffectData.Equals(sAVE_LIGHTING_EFFECT_DATA))
		{
			return false;
		}
		_EffectData = sAVE_LIGHTING_EFFECT_DATA;
		if (CurrentPowerMode == RGBKB_PowerMode.DC)
		{
			_DC_LightLevel = Translate_Layout_LightValue(_EffectData.save_light);
		}
		else
		{
			_AC_LightLevel = Translate_Layout_LightValue(_EffectData.save_light);
		}
		return true;
	}

	internal override void SetBrightnessStrategy(byte brightness, bool saveACDC = true)
	{
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
			_EffectData.save_light = brightness;
			SaveEffectData();
		}
		if (_Mode.Equals(RGBKB_Mode.Night))
		{
			if (brightness < 8)
			{
				_BeforeNightIsZero = true;
				_KeyboardControl.ILM_RGBKB_SetLightingPower(RGBKB_PowerStatus.Off);
				return;
			}
			if (_BeforeNightIsZero)
			{
				_KeyboardControl.UserModeLight = brightness;
				BackgroundColorConverter(_EffectData.save_layout_backgroundcolor);
				NightPowerSwitch(NightPower: true);
				_KeyboardControl.ChangeEffect = false;
				_KeyboardControl.Set_Lighting_Effect(4, _EffectData.save_effect, brightness, _EffectData.save_speed, _EffectData.save_direction, 0, _EffectData.save_layout_color, _EffectData.save_layout_backgroundcolor, _EffectData.save_layout_alphbet);
			}
			else if (_UserModeEffectList.Contains(_EffectData.save_effect))
			{
				_KeyboardControl.UserModeLight = brightness;
			}
			else if (_EffectData.save_effect.Equals(21) || _EffectData.save_effect.Equals(51))
			{
				_KeyboardControl.UserModeLight = brightness;
				_KeyboardControl.Set_Lighting_Effect(4, _EffectData.save_effect, brightness, _EffectData.save_speed, _EffectData.save_direction, 0, _EffectData.save_layout_color, _EffectData.save_layout_backgroundcolor, _EffectData.save_layout_alphbet);
			}
			else
			{
				_KeyboardControl.HID_Set_Brightness_Level_09H(brightness);
			}
			_BeforeNightIsZero = false;
		}
		else
		{
			_KeyboardControl.HID_Set_Brightness_Level_09H(brightness);
		}
	}

	public override async void InitalizeWelcomeKeyboardEffect(RGBKB_PowerStatus power, bool IsAppExists, bool unplug = false)
	{
		try
		{
			_KeyboardControl.GetProjectID().ToString();
			if (IsAppExists)
			{
				if (power.Equals(RGBKB_PowerStatus.On))
				{
					_KeyboardControl.HID_Set_TimeOut_1AH(1, 4, 1);
				}
				else
				{
					_KeyboardControl.HID_Set_TimeOut_1AH(0, 0, 1);
				}
			}
			else if (power.Equals(RGBKB_PowerStatus.On))
			{
				_KeyboardControl.HID_Set_TimeOut_1AH(1, 4, 1);
			}
			else
			{
				_KeyboardControl.HID_Set_TimeOut_1AH(0, 0, 1);
			}
			_KeyboardControl.Set_Lighting_Effect(2, _EffectData.save_effect, _EffectData.save_light, _EffectData.save_speed, _EffectData.save_direction, (byte)_DC_LightLevel, _EffectData.save_layout_color);
			if (_EffectData.save_effect != 0)
			{
				RunEffct(1);
			}
			if (unplug)
			{
				CurrentPowerMode = RGBKB_PowerMode.DC;
				SetBrightnessStrategy(Translate_ITE_LightValue(_DC_LightLevel));
				_EffectData.save_light = Translate_ITE_LightValue(_DC_LightLevel);
				SaveEffectData();
				LogCtrl.Write("In DC Mode Backlight off");
			}
			else
			{
				CurrentPowerMode = RGBKB_PowerMode.AC;
				SetBrightnessStrategy(Translate_ITE_LightValue(_AC_LightLevel));
				_EffectData.save_light = Translate_ITE_LightValue(_AC_LightLevel);
				SaveEffectData();
				LogCtrl.Write("In AC Mode Backlight off");
			}
			_InitIsDone = true;
		}
		catch (Exception)
		{
		}
	}

	public override void SetPowerStatus(RGBKB_PowerStatus powerstatus)
	{
		_PowerStatus = powerstatus;
		if (!_PowerStatus.Equals(RGBKB_PowerStatus.On))
		{
			_KeyboardControl.ILM_RGBKB_SetPower(powerstatus);
			_KeyboardControl.HID_Set_TimeOut_1AH(1, 0, 1);
			SavePowerStatus();
		}
		else
		{
			if (!Monitor.TryEnter(_powerLock, 1500))
			{
				return;
			}
			try
			{
				_KeyboardControl.ILM_RGBKB_SetPower(powerstatus);
				_KeyboardControl.HID_Set_TimeOut_1AH(1, 4, 1);
				if (_EffectData.save_effect != 0)
				{
					RunEffct(0);
				}
				_ = _WelcomeEffectData.save_effect;
				SavePowerStatus();
			}
			finally
			{
				Monitor.Exit(_powerLock);
			}
		}
	}

	public override void UnPlugged()
	{
		byte brightness = Translate_ITE_LightValue(_DC_LightLevel);
		CurrentPowerMode = RGBKB_PowerMode.DC;
		PluggedSetBrightness(brightness);
		if (_KeyboardControl.ILM_RGBKB_GetRGBKeyboardType() == RGBKB_Type.FourZone && _EffectData.save_effect == 34)
		{
			_KeyboardControl.StopMusicTransfer();
		}
	}

	public override void Plugged()
	{
		byte brightness = Translate_ITE_LightValue(_AC_LightLevel);
		CurrentPowerMode = RGBKB_PowerMode.AC;
		PluggedSetBrightness(brightness);
		if (_KeyboardControl.ILM_RGBKB_GetRGBKeyboardType() == RGBKB_Type.FourZone && _EffectData.save_effect == 34)
		{
			RunEffct(0);
		}
	}

	internal override void SetACDCLight(bool unplug, uint aclevel, uint dclevel)
	{
		if (unplug)
		{
			CurrentPowerMode = RGBKB_PowerMode.DC;
			byte b = Translate_ITE_LightValue(dclevel);
			SetBrightnessStrategy(b);
			_EffectData.save_light = b;
			SaveEffectData();
			LogCtrl.Write("In DC Mode Backlight Now bcaklight : " + _EffectData.save_light);
			_DC_LightLevel = dclevel;
		}
		else
		{
			CurrentPowerMode = RGBKB_PowerMode.AC;
			byte b2 = Translate_ITE_LightValue(aclevel);
			SetBrightnessStrategy(b2);
			_EffectData.save_light = b2;
			SaveEffectData();
			LogCtrl.Write("In AC Mode Backlight Now bcaklight : " + _EffectData.save_light);
			_AC_LightLevel = aclevel;
		}
	}

	public override void SetBrinessByScanCode(int scancode)
	{
		switch (scancode)
		{
		case 177:
		case 178:
		{
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
				num = ((num >= 0) ? (num - 1) : 0u);
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
			RGBKB_Event_Data event_data2 = new RGBKB_Event_Data
			{
				event_id = RGBKB_EventID.Brightness_update,
				envet_data_len = 1u,
				event_data = new byte[1]
			};
			event_data2.event_data[0] = (byte)Translate_Layout_LightValue(_EffectData.save_light);
			ScanCodeUpdatedBrightness(event_data2);
			break;
		}
		case 185:
		{
			LogCtrl.Write("HID_Default Circle B6 : scan code: " + scancode);
			uint save_light = _EffectData.save_light;
			save_light = (save_light + 1) % 100;
			_EffectData.save_light = Convert.ToByte(save_light);
			SetBrightnessStrategy(_EffectData.save_light);
			RGBKB_Event_Data event_data = new RGBKB_Event_Data
			{
				event_id = RGBKB_EventID.Brightness_update,
				envet_data_len = 1u,
				event_data = new byte[1]
			};
			event_data.event_data[0] = (byte)Translate_Layout_LightValue(_EffectData.save_light);
			ScanCodeUpdatedBrightness(event_data);
			break;
		}
		}
	}

	public override uint GetBrightness()
	{
		return Convert.ToUInt32(_EffectData.save_light);
	}

	public override void CloseAnimation()
	{
		if (!_CloseAnimation || _PowerStatus != RGBKB_PowerStatus.On)
		{
			return;
		}
		try
		{
			for (int num = _EffectData.save_light; num > 0; num -= 16)
			{
				SetBrightnessStrategy((byte)num, saveACDC: false);
				Thread.Sleep(num);
			}
			SetBrightnessStrategy(0, saveACDC: false);
		}
		catch
		{
		}
	}

	public override void RunEffct(byte SAVED = 0)
	{
		try
		{
			if (!_PowerStatus.Equals(RGBKB_PowerStatus.On))
			{
				return;
			}
			LogCtrl.Write("Run Effect in QC " + _EffectData.save_effect);
			SAVED = 1;
			if (_EffectData.save_mode == RGBKB_Mode.Lighting)
			{
				_KeyboardControl.m_effect_type = GetEffectType(_EffectData.save_effect);
				_KeyboardControl.ChangeEffect = ((_LastEffectRun != _EffectData.save_effect) ? true : false);
				NightModeReflash(_EffectData.save_mode);
				if (_EffectData.save_effect == 21)
				{
					RGB_S item = _EffectData.save_layout_color.ColorBuffer.First();
					RGBKB_Color save_layout_color = new RGBKB_Color
					{
						isCircular = true,
						ColorBlocks = 4u
					};
					List<RGB_S> list = new List<RGB_S>();
					for (int i = 0; i < 4; i++)
					{
						list.Add(item);
					}
					save_layout_color.ColorBuffer = list.ToArray();
					_EffectData.save_layout_color = save_layout_color;
				}
				_KeyboardControl.Set_Lighting_Effect(2, _EffectData.save_effect, _EffectData.save_light, _EffectData.save_speed, _EffectData.save_direction, SAVED, _EffectData.save_layout_color, 0, _EffectData.save_layout_alphbet);
				SaveEffectData();
				_LastEffectRun = _EffectData.save_effect;
			}
			else if (_EffectData.save_mode == RGBKB_Mode.Night)
			{
				_KeyboardControl.m_effect_type = GetEffectType(_EffectData.save_effect);
				_KeyboardControl.ChangeEffect = ((_LastEffectRun != _EffectData.save_effect) ? true : false);
				NightModeReflash(_EffectData.save_mode);
				if (_EffectData.save_light == 0)
				{
					_KeyboardControl.UserModeLight = 0;
					_BeforeNightIsZero = true;
				}
				else
				{
					_KeyboardControl.UserModeLight = _EffectData.save_light;
					_BeforeNightIsZero = false;
				}
				if (_EffectData.save_effect == 21)
				{
					RGB_S item2 = _EffectData.save_layout_color.ColorBuffer.First();
					RGBKB_Color save_layout_color2 = new RGBKB_Color
					{
						ColorBlocks = 4u
					};
					List<RGB_S> list2 = new List<RGB_S>();
					for (int j = 0; j < 4; j++)
					{
						list2.Add(item2);
					}
					save_layout_color2.ColorBuffer = list2.ToArray();
					_EffectData.save_layout_color = save_layout_color2;
				}
				_KeyboardControl.Set_Lighting_Effect(4, _EffectData.save_effect, _EffectData.save_light, _EffectData.save_speed, _EffectData.save_direction, SAVED, _EffectData.save_layout_color, _EffectData.save_layout_backgroundcolor, _EffectData.save_layout_alphbet);
				if (_EffectData.save_light == 0)
				{
					_KeyboardControl.ILM_RGBKB_SetLightingPower(RGBKB_PowerStatus.Off);
				}
				SaveEffectData();
				_LastEffectRun = _EffectData.save_effect;
			}
			else
			{
				LogCtrl.Write("Run Effect But Power Off ");
			}
		}
		catch (Exception)
		{
		}
	}

	internal override void SaveEffectData()
	{
		if (_EffectData.save_mode != RGBKB_Mode.Welcome)
		{
			string text = _KeyboardControl?.GetProjectID().ToString();
			SettingsStorageExtensions.SaveAsync(_KeyboardControl?.ILM_RGBKB_GetRGBKeyboardType().ToString(), text + "_LastEffect", _EffectData);
			if (CurrentPowerMode == RGBKB_PowerMode.AC)
			{
				SettingsStorageExtensions.SaveAsync("", _SaveACLight, _AC_LightLevel);
			}
			else if (CurrentPowerMode == RGBKB_PowerMode.DC)
			{
				SettingsStorageExtensions.SaveAsync("", _SaveDCLight, _DC_LightLevel);
			}
		}
	}
}
