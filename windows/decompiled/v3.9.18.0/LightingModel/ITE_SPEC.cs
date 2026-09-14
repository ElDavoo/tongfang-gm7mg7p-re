using System;
using System.Collections.Generic;

namespace LightingModel
{
	internal class ITE_SPEC
	{
		internal const ushort VID = 1165;

		internal readonly List<ushort> PIDList;

		internal readonly List<ushort> LBPIDList;

		internal const ushort USAGE = 1;

		internal const ushort USAGE_PAGE_4Zone = 65298;

		internal const ushort USAGE_PAGE_ME_1ST = 65282;

		internal const ushort USAGE_PAGE_ME_2ND = 65283;

		internal const ushort USAGE_PAGE_Ligbar = 65283;

		internal const byte MS_RESERVED = 0;

		internal const uint RGB_LED_NUM = 126u;

		internal const byte Contorl_LED_Off = 1;

		internal const byte Contorl_LED_Default = 2;

		internal const byte Contorl_LED_Welcome = 3;

		internal const byte Contorl_LED_Night = 4;

		internal const byte NV_SAVE = 1;

		internal const byte NV_NOT_SAVE = 0;

		internal const byte EFFECT_STATIC = 1;

		internal const byte EFFECT_BREATHING = 2;

		internal const byte EFFECT_REACTIVE = 4;

		internal const byte EFFECT_WAVE = 3;

		internal const byte EFFECT_RAINBOW = 5;

		internal const byte EFFECT_RIPPLE = 6;

		internal const byte EFFECT_NOMO = 8;

		internal const byte EFFECT_MARQUEE = 9;

		internal const byte EFFECT_RAINDROP = 10;

		internal const byte EFFECT_STACK = 12;

		internal const byte EFFECT_IMPACT = 13;

		internal const byte EFFECT_AURORA = 14;

		internal const byte EFFECT_NEON = 15;

		internal const byte EFFECT_SPARK = 17;

		internal const byte EFFECT_FLASH = 18;

		internal const byte EFFECT_MIX = 19;

		internal const byte EFFECT_GAMING = 21;

		internal const byte EFFECT_RIPPLEO = 22;

		internal const byte EFFECT_ALPHABET = 23;

		internal const byte EFFECT_MUSIC = 34;

		internal const byte EFFECT_USERMODE = 51;

		internal const byte EFFECT_THINKING = 33;

		internal const byte EFFECT_STARSPARK = 24;

		internal const byte EFFECT_STARHITTING = 25;

		internal const byte EFFECT_BATTERYPERCENT = 35;

		internal const byte EFFECT_UNKNOWN = byte.MaxValue;

		internal const byte EFFECT_TYPE_NIGHTMODE = 254;

		internal const byte EFFECT_TYPE_FW = 0;

		internal const byte EFFECT_TYPE_ROW = 1;

		internal const byte EFFECT_TYPE_PICTURE = 2;

		internal const byte EFFECT_TYPE_MUSIC = 3;

		internal const byte EFFECT_TYPE_AP = 4;

		internal const ushort EC_RGBKBBKL_LEVEL_UPDATE = 240;

		internal const ushort EC_RGBKBBKL_LEVEL_DOWN = 177;

		internal const ushort EC_RGBKBBKL_LEVEL_UP = 178;

		internal const ulong EC_PROJECT_ID_BYTE = 1856uL;

		internal const ulong EC_MEZone_2n1p_ID_BYTE = 1852uL;

		internal const ulong EC_AP_OEM_BYTE = 1857uL;

		internal const byte EC_bitOnKeyPressOn = 8;

		internal const byte EC_PROJECT_LEGANCY = 0;

		internal const byte EC_PROJECT_GIxKN = 1;

		internal const byte EC_PROJECT_GJxKN = 2;

		internal const byte EC_PROJECT_GKxCN = 3;

		internal const byte EC_PROJECT_GIxCN = 4;

		internal const byte EC_PROJECT_GJxCN = 5;

		internal const byte EC_PROJECT_GK5CN_X = 6;

		internal const byte EC_PROJECT_GK7CN_S = 7;

		internal const byte EC_PROJECT_GK7CPCS_GK5CQ7Z = 8;

		internal const byte EC_PROJECT_IDP = 11;

		internal const byte EC_PROJECT_ID6Y = 12;

		internal const byte EC_PROJECT_ID7Y = 13;

		internal const byte EC_PROJECT_PF4MU_PF4MN_PF5MU = 14;

		internal const byte EC_PROJECT_CML_Gaming = 15;

		internal const byte EC_PROJECT_GK7NXXR = 16;

		internal const byte EC_PROJECT_GM5MU1Y = 17;

		internal const byte EC_KBID_101 = 25;

		internal const byte EC_KBID_101M = 41;

		internal const byte EC_KBID_102 = 17;

		internal const byte EC_KBID_102M = 33;

		internal const byte EC_KBID_85 = 25;

		internal const byte EC_KBID_86 = 17;

		internal const byte EC_KBID_87 = 73;

		internal const byte EC_KBID_88 = 65;

		internal const byte EC_KBID_97 = 57;

		internal const byte EC_KBID_98 = 49;

		internal const byte EC_KBID_99 = 121;

		internal const byte EC_KBID_100 = 113;

		internal byte Ver_High;

		internal byte Ver_Low;

		internal byte Ver_Test;

		internal byte Ver_Customer;

		public ITE_SPEC()
		{
			//IL_0003: Unknown result type (might be due to invalid IL or missing references)
			//IL_0006: Unknown result type (might be due to invalid IL or missing references)
			if ((sbyte)/*Error near IL_0001: Stack underflow*/ == 0)
			{
				/*Error: Invalid branch target*/;
			}
			_ = (byte)(/*Error near IL_0007: Stack underflow*/ << (int)(long)checked((IntPtr)(long)(ushort)(/*Error near IL_0004: Stack underflow*/ - /*Error near IL_0004: Stack underflow*/)));
			/*Error near IL_0008: Unknown opcode: 0x77*/;
		}
	}
}
