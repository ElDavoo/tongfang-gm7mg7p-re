using System;
using Microsoft.Win32;
using Utility;

namespace LightingModel;

public class LM_Manager
{
	private bool m_bInitStatus;

	private ILM_RGBKB m_ILM_RGBKB;

	private LM_ITE_RGB m_LM_ITE_RGB;

	private LM_ITE_RGB m_LM_ITE_RGBLB;

	private LM_EC_RGB m_LM_EC_RGB;

	public RGBKB_Solution m_KB_Solution;

	public RGBKB_Type m_KB_Type;

	public bool LM_Init(string DefaultTool = null)
	{
		try
		{
			m_LM_ITE_RGB = new LM_ITE_RGB();
			m_LM_EC_RGB = new LM_EC_RGB();
			if (DefaultTool != null)
			{
				LogCtrl.TraceMessage("DefaultTool = " + DefaultTool, "LM_Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\LM_Manager.cs", 39);
				if (m_LM_ITE_RGB.ILM_RGBKB_Init(DefaultTool))
				{
					LogCtrl.Write("LM_Manager|LM_Init : ITE solution");
					m_KB_Solution = RGBKB_Solution.ITE;
					m_ILM_RGBKB = m_LM_ITE_RGB;
					m_KB_Type = m_ILM_RGBKB.ILM_RGBKB_GetRGBKeyboardType();
					m_bInitStatus = true;
				}
				else if (m_LM_EC_RGB.ILM_RGBKB_Init(DefaultTool))
				{
					LogCtrl.Write("LM_Manager|LM_Init : EC solution");
					m_KB_Solution = RGBKB_Solution.EC;
					m_ILM_RGBKB = m_LM_EC_RGB;
					m_KB_Type = m_ILM_RGBKB.ILM_RGBKB_GetRGBKeyboardType();
					m_bInitStatus = true;
				}
			}
			else
			{
				LogCtrl.TraceMessage("DefaultTool = null", "LM_Init", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\LightingModel\\LM_Manager.cs", 61);
				if (m_LM_ITE_RGB.ILM_RGBKB_Init())
				{
					LogCtrl.Write("LM_Manager|LM_Init : ITE solution");
					m_KB_Solution = RGBKB_Solution.ITE;
					m_ILM_RGBKB = m_LM_ITE_RGB;
					m_KB_Type = m_ILM_RGBKB.ILM_RGBKB_GetRGBKeyboardType();
					m_bInitStatus = true;
				}
				else if (m_LM_EC_RGB.ILM_RGBKB_Init())
				{
					LogCtrl.Write("LM_Manager|LM_Init : EC solution");
					m_KB_Solution = RGBKB_Solution.EC;
					m_ILM_RGBKB = m_LM_EC_RGB;
					m_KB_Type = m_ILM_RGBKB.ILM_RGBKB_GetRGBKeyboardType();
					m_bInitStatus = true;
				}
			}
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\ItemSupport", "KeyboardType", m_KB_Type, RegistryValueKind.DWord);
			if (!m_bInitStatus)
			{
				LogCtrl.Write("LM_Manager|LM_Init : Not RGB Keyboard moudle");
				m_bInitStatus = false;
			}
		}
		catch
		{
			m_bInitStatus = false;
		}
		return m_bInitStatus;
	}

	public bool LB_Init(string DefaultTool = null)
	{
		try
		{
			m_LM_ITE_RGBLB = new LM_ITE_RGB();
			if (DefaultTool != null)
			{
				m_LM_ITE_RGB.ILM_RGBLB_Init(DefaultTool);
				LogCtrl.Write("LM_Manager|LM_Init : ITE solution");
				m_KB_Solution = RGBKB_Solution.ITE;
				m_ILM_RGBKB = m_LM_ITE_RGBLB;
				m_KB_Type = m_ILM_RGBKB.ILM_RGBKB_GetRGBKeyboardType();
				m_bInitStatus = true;
			}
			else if (m_LM_ITE_RGBLB.ILM_RGBLB_Init())
			{
				LogCtrl.Write("LM_Manager|LB_Init for HidLightbar : ITE solution");
				m_KB_Solution = RGBKB_Solution.ITE;
				m_ILM_RGBKB = m_LM_ITE_RGBLB;
				m_KB_Type = m_ILM_RGBKB.ILM_RGBKB_GetRGBKeyboardType();
				m_bInitStatus = true;
			}
		}
		catch (Exception)
		{
			m_bInitStatus = false;
		}
		return m_bInitStatus;
	}

	public bool LM_DeInit()
	{
		m_bInitStatus = false;
		return false;
	}

	public object GetITE_RGB()
	{
		if (m_LM_ITE_RGB != null)
		{
			return m_LM_ITE_RGB.GetLM_ITE_RGB_Self();
		}
		if (m_LM_ITE_RGBLB != null)
		{
			return m_LM_ITE_RGBLB.GetLM_ITE_RGB_Self();
		}
		return null;
	}

	public object GetEC_RGB()
	{
		return m_LM_EC_RGB;
	}

	public bool LM_SetPower(RGBKB_PowerStatus powerStatus)
	{
		if (!m_bInitStatus)
		{
			return false;
		}
		return m_ILM_RGBKB.ILM_RGBKB_SetPower(powerStatus);
	}

	public bool LM_GetPower()
	{
		return m_ILM_RGBKB.ILM_RGBKB_GetPower();
	}

	public bool LM_SetPowerSaving(RGBKB_PowerStatus powerStatus)
	{
		_ = m_bInitStatus;
		return false;
	}

	public bool LM_SetEffectALL(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, uint layout_light, uint layout_speed, RGBKB_Direction layout_direction, RGBKB_Color layout_color, RGBKB_NV_SAVE layout_save, int layout_backgroundcolor = 0, string layout_alphabet = null)
	{
		if (!m_bInitStatus)
		{
			return false;
		}
		return m_ILM_RGBKB.ILM_RGBKB_SetEffectALL(layout_mode, layout_effect, layout_light, layout_speed, layout_direction, layout_color, layout_save, layout_backgroundcolor, layout_alphabet);
	}

	public bool LM_SetColor(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, RGBKB_Color layout_color)
	{
		if (!m_bInitStatus)
		{
			return false;
		}
		return m_ILM_RGBKB.ILM_RGBKB_SetColor(layout_mode, layout_effect, layout_color);
	}

	public bool LM_GetEffect(RGBKB_Mode query_mode, ref RGBKB_Effect current_effect)
	{
		if (!m_bInitStatus)
		{
			return false;
		}
		return m_ILM_RGBKB.ILM_RGBKB_GetEffect(query_mode, ref current_effect);
	}

	public bool LM_SetLightingLevel(uint level)
	{
		if (!m_bInitStatus)
		{
			return false;
		}
		return m_ILM_RGBKB.ILM_RGBKB_SetBrighntess(level);
	}

	public bool LM_GetLightingLevel(ref uint level)
	{
		if (!m_bInitStatus)
		{
			return false;
		}
		return m_ILM_RGBKB.ILM_RGBKB_GetBrighntess(ref level);
	}

	public string LM_GetFirmwareVersion()
	{
		if (!m_bInitStatus)
		{
			return "";
		}
		return m_ILM_RGBKB.ILM_RGBKB_GetFirmwareVersion();
	}

	public bool LM_SaveLightingLevel(uint level)
	{
		if (!m_bInitStatus)
		{
			return false;
		}
		return m_ILM_RGBKB.ILM_RGBKB_SaveLightingLevel(level);
	}
}
