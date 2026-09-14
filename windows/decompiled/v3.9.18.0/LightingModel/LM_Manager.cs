using System;

namespace LightingModel
{
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
		//Invalid MethodBodyBlock: Invalid method header: 0xE4
		}

		public bool LB_Init(string DefaultTool = null)
		{
			_ = (IntPtr)/*Error near IL_0001: Stack underflow*/;
			/*Error near IL_0002: Unknown opcode: 0xCE*/;
		}

		public bool LM_DeInit()
		{
			/*Error: Unknown opcode: 0xB0*/;
		}

		public unsafe object GetITE_RGB()
		{
			((double[])/*Error near IL_0001: Stack underflow*/)[/*Error near IL_0001: Stack underflow*/] = (double)/*Error near IL_0001: Stack underflow*/;
			_ = *(ushort*)(IntPtr)/*Error near IL_0001: ldloc 3 (out-of-bounds)*/;
			/*Error near IL_0003: Unknown opcode: 0x77*/;
		}

		public object GetEC_RGB()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xEC
		}

		public bool LM_SetPower(RGBKB_PowerStatus powerStatus)
		{
			/*Error: Unknown opcode: 0xB1*/;
		}

		public bool LM_GetPower()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xDF 0x19
		}

		public bool LM_SetPowerSaving(RGBKB_PowerStatus powerStatus)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB5
		}

		public bool LM_SetEffectALL(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, uint layout_light, uint layout_speed, RGBKB_Direction layout_direction, RGBKB_Color layout_color, RGBKB_NV_SAVE layout_save, int layout_backgroundcolor = 0, string layout_alphabet = null)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA3 0x0C
		}

		public bool LM_SetColor(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, RGBKB_Color layout_color)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x98
		}

		public bool LM_GetEffect(RGBKB_Mode query_mode, ref RGBKB_Effect current_effect)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB3 0x97
		}

		public bool LM_SetLightingLevel(uint level)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xCF 0x2B
		}

		public bool LM_GetLightingLevel(ref uint level)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA0
		}

		public string LM_GetFirmwareVersion()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xF1
		}

		public bool LM_SaveLightingLevel(uint level)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x83 0x7A
		}
	}
}
