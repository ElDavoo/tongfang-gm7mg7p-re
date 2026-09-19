using System;
using MyControlCenter;
using MyECIO;
using Utility;

namespace LightingModel;

internal class LM_EC_RGB : EC_SPEC, ILM_RGBKB
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private RGBKB_Type m_EC_KB_Type;

	private byte m_Project_ID;

	public bool ILM_RGBKB_Init(string IsDefaultTool)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1856, ref Data);
		m_Project_ID = (byte)Convert.ToUInt64(Data);
		if (NvramVariable.IsSingleColorKeyboardDetection() == 1)
		{
			return false;
		}
		Data = 0;
		EcCtrl.Read(GetType().Name, 1894, ref Data);
		if (((byte)Convert.ToUInt64(Data) & 4) == 4)
		{
			m_EC_KB_Type = RGBKB_Type.SingleZone;
			return true;
		}
		return false;
	}

	public bool ILM_RGBKB_Init()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1856, ref Data);
		m_Project_ID = (byte)Convert.ToUInt64(Data);
		if (NvramVariable.IsSingleColorKeyboardDetection() == 1)
		{
			return false;
		}
		Data = 0;
		EcCtrl.Read(GetType().Name, 1894, ref Data);
		if (((byte)Convert.ToUInt64(Data) & 4) == 4)
		{
			m_EC_KB_Type = RGBKB_Type.SingleZone;
			return true;
		}
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_Init()
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_Init
		return this.ILM_RGBKB_Init();
	}

	public bool ILM_RGBKB_SetPower(RGBKB_PowerStatus PowerStatus)
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT", "ILM_RGBKB_SetPower", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 278);
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetPower(RGBKB_PowerStatus PowerStatus)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetPower
		return this.ILM_RGBKB_SetPower(PowerStatus);
	}

	public bool ILM_RGBKB_GetPower()
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT", "ILM_RGBKB_GetPower", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 284);
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_GetPower()
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetPower
		return this.ILM_RGBKB_GetPower();
	}

	public RGBKB_Type ILM_RGBKB_GetRGBKeyboardType()
	{
		return m_EC_KB_Type;
	}

	RGBKB_Type ILM_RGBKB.ILM_RGBKB_GetRGBKeyboardType()
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetRGBKeyboardType
		return this.ILM_RGBKB_GetRGBKeyboardType();
	}

	public string ILM_RGBKB_GetFirmwareVersion()
	{
		return "";
	}

	string ILM_RGBKB.ILM_RGBKB_GetFirmwareVersion()
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetFirmwareVersion
		return this.ILM_RGBKB_GetFirmwareVersion();
	}

	public bool ILM_RGBKB_SetEffectALL(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, uint layout_light, uint layout_speed, RGBKB_Direction layout_direction, RGBKB_Color layout_color, RGBKB_NV_SAVE layout_save, int layout_backgroundcolor = 0, string layout_alphabet = null)
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT", "ILM_RGBKB_SetEffectALL", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 300);
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetEffectALL(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, uint layout_light, uint layout_speed, RGBKB_Direction layout_direction, RGBKB_Color layout_color, RGBKB_NV_SAVE layout_save, int layout_backgroundcolor = 0, string layout_alphabet = null)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetEffectALL
		return this.ILM_RGBKB_SetEffectALL(layout_mode, layout_effect, layout_light, layout_speed, layout_direction, layout_color, layout_save, layout_backgroundcolor, layout_alphabet);
	}

	public bool ILM_RGBKB_GetEffectALL(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect, ref uint layout_light, ref uint layout_speed, ref RGBKB_Direction layout_direction, ref RGBKB_Color layout_color)
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT", "ILM_RGBKB_GetEffectALL", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 306);
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_GetEffectALL(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect, ref uint layout_light, ref uint layout_speed, ref RGBKB_Direction layout_direction, ref RGBKB_Color layout_color)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetEffectALL
		return this.ILM_RGBKB_GetEffectALL(layout_mode, ref layout_effect, ref layout_light, ref layout_speed, ref layout_direction, ref layout_color);
	}

	public bool ILM_RGBKB_SetEffect(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect)
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT", "ILM_RGBKB_SetEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 312);
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetEffect(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetEffect
		return this.ILM_RGBKB_SetEffect(layout_mode, layout_effect);
	}

	public bool ILM_RGBKB_GetEffect(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect)
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT", "ILM_RGBKB_GetEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 318);
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_GetEffect(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetEffect
		return this.ILM_RGBKB_GetEffect(layout_mode, ref layout_effect);
	}

	public bool ILM_RGBKB_SetBrighntess(uint layout_brightness)
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT, layout_brightness = " + layout_brightness, "ILM_RGBKB_SetBrighntess", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 324);
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetBrighntess(uint layout_brightness)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetBrighntess
		return this.ILM_RGBKB_SetBrighntess(layout_brightness);
	}

	public bool ILM_RGBKB_GetBrighntess(ref uint layout_brightness)
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT", "ILM_RGBKB_GetBrighntess", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 330);
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_GetBrighntess(ref uint layout_brightness)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetBrighntess
		return this.ILM_RGBKB_GetBrighntess(ref layout_brightness);
	}

	public bool ILM_RGBKB_SetSpeed(uint layout_speed)
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT", "ILM_RGBKB_SetSpeed", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 336);
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetSpeed(uint layout_speed)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetSpeed
		return this.ILM_RGBKB_SetSpeed(layout_speed);
	}

	public bool ILM_RGBKB_SetDirection(uint layout_direction)
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT", "ILM_RGBKB_SetDirection", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 342);
		return false;
	}

	public bool ILM_RGBKB_SetColor(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, RGBKB_Color layout_color)
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT", "ILM_RGBKB_SetColor", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 348);
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetColor(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, RGBKB_Color layout_color)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetColor
		return this.ILM_RGBKB_SetColor(layout_mode, layout_effect, layout_color);
	}

	public bool ILM_RGBKB_SaveLightingLevel(uint layout_light)
	{
		LogCtrl.TraceMessage("NEEDS IMPLEMENT", "ILM_RGBKB_SaveLightingLevel", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\RGBKeyboard_EC.cs", 354);
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SaveLightingLevel(uint layout_light)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SaveLightingLevel
		return this.ILM_RGBKB_SaveLightingLevel(layout_light);
	}

	public byte GetProjectID()
	{
		return m_Project_ID;
	}
}
