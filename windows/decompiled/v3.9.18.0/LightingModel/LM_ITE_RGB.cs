using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Media;
using AudioLib;
using GCUService.MySystem;
using MyControlCenter.MyRgbKeyboard;
using MyECIO;
using UsbHidModel;

namespace LightingModel
{
	internal class LM_ITE_RGB : ITE_SPEC, ILM_RGBKB
	{
		private MyEcCtrl EcCtrl;

		private HIDManager m_HIDManager;

		private FileStream m_HIDDevice;

		private RGBKB_Type m_ITE_KB_Type;

		private byte m_Project_ID;

		public byte m_effect_type;

		private static SAVE_LIGHTING_EFFECT_DATA m_save_lighting_data;

		private bool m_enableOnkeyPressed;

		private bool m_light_lock;

		private Task m_ap_effect_task;

		private bool m_ap_effect_task_stop;

		private SAVE_LIGHTING_EFFECT_DATA m_ap_effect_data;

		private BatteryPercentManger battry;

		private byte NightMode;

		private int NightModeSelectColorIndex;

		private AudioData audioData;

		public int ColShift;

		public int ColRightShift;

		private bool _SingleTimeChangeFlag;

		private byte _asyncSingleBrightness;

		private List<RGBKB_Type> MEZone_2p1ndSeries;

		private List<RGBKB_Type> MEZone_2p2ndSeries;

		private List<RGBKB_Type> MEZone_LightbarSeries;

		private bool BatteryEnable;

		private List<Color> DefalutColorList;

		private bool BeforeLevelIsDisable;

		private object _08HLock;

		private Stopwatch sw1;

		private Dictionary<RGBKB_Type, AudioData> audioDevices;

		private List<List<RGB_S>> VerticalColorList;

		private Stopwatch sw;

		private int AnimationShift;

		private int shiftCount;

		private int shiftvalue;

		private float EqualsMachMax;

		private float EqualsMachMin;

		private object lock_12h_test;

		private object usbTransferLock;

		public byte UserModeLight;

		private List<byte[]> perKBBuffer;

		private List<byte[]> perLBBuffer;

		private object usermodeLock;

		private bool KBuserModeLock;

		private bool LBuserModeLock;

		private string AlphabetString;

		public bool ChangeEffect;

		private Thread SingleChangeThread;

		private object led_off_lock;

		private static event RGBKB_Event_Handler m_Layout_Event_handler
		{
			[CompilerGenerated]
			add
			{
				/*Error: Metadata token must be either a methoddef, memberref or methodspec*/;
			}
			[CompilerGenerated]
			remove
			{
			//Invalid MethodBodyBlock: Invalid method header: 0xA0
			}
		}

		private unsafe void BatteryEable(bool Enable)
		{
			*(_003F*)(IntPtr)/*Error near IL_0001: Stack underflow*/ = /*Error near IL_0001: Stack underflow*/;
			/*Error: End of method reached without returning.*/;
		}

		private void Battry_LifePercentChange(object sender, EventArgs e)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xAB 0x76
		}

		public void IndicatorEffect(string percent)
		{
			//IL_0001: Invalid comparison between Unknown and I4
			if ((int)/*Error near IL_0003: Stack underflow*/ != checked((short)/*Error near IL_0001: Stack underflow*/))
			{
				/*Error: Invalid branch target*/;
			}
			/*Error near IL_0003: Unknown opcode: 0xB0*/;
		}

		public RGB_S[] PercentEffect(Color foregroundColor, Color backgroundColor, RGB_S[] keys, double value, double total, double flash_past = 0.0, bool flash_reversed = false, bool blink_background = false)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xF3 0x8D
		}

		private void SetOneKey(ref RGB_S currentColor, Color color)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x00
		}

		public byte GetProjectID()
		{
			//IL_0001: Invalid comparison between Unknown and I4
			if ((int)/*Error near IL_0003: Stack underflow*/ > 0)
			{
				/*Error: Invalid branch target*/;
			}
			if (checked((long)/*Error near IL_0004: Stack underflow*/) == 0L)
			{
				/*Error: Invalid branch target*/;
			}
			((sbyte[])/*Error near IL_0007: Stack underflow*/)[/*Error near IL_0007: Stack underflow*/] = (sbyte)/*Error near IL_0007: Stack underflow*/;
			checked
			{
				_ = (sbyte)/*Error near IL_0008: Stack underflow*/;
				/*Error near IL_0008: Unknown opcode: 0xA8*/;
			}
		}

		public LM_ITE_RGB GetLM_ITE_RGB_Self()
		{
			/*Error: Unknown opcode: 0xA8*/;
		}

		private unsafe void ScanCode_Hnadler(int scancode)
		{
			//IL_0003: Unknown result type (might be due to invalid IL or missing references)
			_ = /*Error near IL_0004: Stack underflow*/% (double)(*(ulong*)2);
			/*Error near IL_0004: Unknown opcode: 0xBE*/;
		}

		private void Light_Lock()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xAD
		}

		private void AP_Effect_Task()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA7 0xA2
		}

		private bool CheckCollsion(LEDActor lEDActor, List<LEDActor> correctLed)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x08
		}

		private RGB_S[] ConvertToLightBarMap(RGB_S[] _IntoColorList)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x3F 0xDB
		}

		public bool HID_Set_Effect_Type_08H(byte Control, byte Effect, byte Speed, byte Light, byte ColorIndex, byte Direction, byte Save)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xF1
		}

		public bool HID_Set_Brightness_Level_09H(byte level)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xFD
		}

		private bool HID_Get_FirmwareVersion_80H(ref byte Ver_High, ref byte Ver_Low, ref byte Ver_Test, ref byte Ver_Customer)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x0D
		}

		public bool HID_Set_TimeOut_1AH(byte enable, byte time, byte save)
		{
			_ = (UIntPtr)/*Error near IL_0001: Stack underflow*/;
			/*Error near IL_0001: Invalid metadata token*/;
		}

		public bool HID_Get_Effect_Type_88H(ref byte Control, ref byte Effect, ref byte Speed, ref byte Light, ref byte ColorIndex, ref byte Direction)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x51
		}

		private bool HID_Set_Picture_12H(byte Saved)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB4
		}

		private bool HID_Set_Color_14H(byte Index, byte R, byte G, byte B)
		{
			checked
			{
				_ = (IntPtr)/*Error near IL_0001: Stack underflow*/;
				_ = 6;
				_ = 1.7113484E+23f;
				/*Error near IL_0007: Unknown opcode: 0xBC*/;
			}
		}

		private bool HID_Set_RowIndex_16H(byte RowIndex)
		{
			/*Error: Invalid branch target*/;
		}

		private bool HID_Set_RowIndex_26H(byte RowIndex)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x90
		}

		private bool HID_Set_RowIndex_12H(byte RowIndex)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xFC
		}

		private void AudioData_WaveOutCenterHorizontalEventHandler(object sender)
		{
		//Invalid MethodBodyBlock: Invalid local signature token: 0x7F5E41B3
		}

		private void AudioData_WaveOutHorizontalEventHandler(object sender)
		{
			/*Error: Unknown opcode: 0xCC*/;
		}

		private void AudioData_WaveOutEventHandler(object sender)
		{
			/*Error: Unknown opcode: 0xC7*/;
		}

		private float AdjustMeterParam(byte speed)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x7D
		}

		private bool DLL_SetMusicMode(bool enable, byte light_level = 4, byte speed = 1, byte direction = 0, RGB_S[] colorBuffer = null)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x4F 0x06
		}

		private void AudioData_Lightbar2EventHandler(object sender)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xE7 0x51
		}

		private void AudioData_LightbarEventHandler(object sender)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB7 0xED
		}

		public void ResetEqualMachine()
		{
			/*Error: Read out of bounds.*/;
		}

		private float EqualMachine(List<float> meterValue, byte target)
		{
			if (/*Error near IL_0005: Stack underflow*/ == /*Error near IL_0005: Stack underflow*/)
			{
				/*Error: Invalid branch target*/;
			}
			if (/*Error near IL_000a: Stack underflow*/ >= /*Error near IL_000a: Stack underflow*/)
			{
				/*Error: Invalid branch target*/;
			}
			/*Error near IL_000a: Read out of bounds.*/;
		}

		private void AudioData_KeybaoradWaveBrightnewssEventHandlerForAll(object sender)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xEF 0xEC
		}

		private void AudioData_KeyBoardWaveBrightnessEventHandler(object sender)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB3 0xBD
		}

		private bool Disable_EC_OnkeyPressed()
		{
			checked
			{
				_ = (int)/*Error near IL_0001: Stack underflow*/;
				/*Error near IL_0001: ldarg 2 (out-of-bounds)*/;
				/*Error near IL_0002: Unknown opcode: 0xCD*/;
			}
		}

		private bool Enable_EC_OnkeyPressed(byte effect, byte direction)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x4F 0x9D
		}

		public static void log(string strLog)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x51
		}

		private RGB_S BackgroundColorConverter(int colorindex)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xB0
		}

		private RGB_S APBackgroundColorConverter(int colorindex)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x05
		}

		private bool Set_ITE_Effect_Type_UserMode_Lightbar(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x39
		}

		private bool Set_ITE_Effect_Type_UserMode_Lightbar12h(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x55
		}

		private bool Set_ITE_Effect_Type_UserMode_Lightbar2(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh, int StartIndex)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x7D
		}

		public static bool compareArr(byte[] arr1, byte[] arr2)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x40
		}

		private bool CheckKBBufferPlan(int row, byte[] buffer)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x69
		}

		private bool CheckLBBufferPlan(int row, byte[] buffer)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x48
		}

		private bool Set_ITE_Effect_Type_UserMode(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh)
		{
			/*Error: Invalid metadata token*/;
		}

		private bool Set_ITE_Effect_Type_UserMode_Dynamic(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x88
		}

		private bool Set_ITE_Effect_Type_StaticMode(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xA8
		}

		private bool Set_ITE_Effect_Type_FwMode(byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xAD
		}

		private bool Set_ITE_Effect_Type_ApMode(byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color)
		{
			//IL_0000: Unknown result type (might be due to invalid IL or missing references)
			checked
			{
				_ = (long)(ushort)(/*Error near IL_0001: Stack underflow*/ - /*Error near IL_0001: Stack underflow*/);
				/*Error near IL_0003: ldloc 0 (out-of-bounds)*/;
				/*Error near IL_0004: Unknown opcode: 0xF2*/;
			}
		}

		public bool Set_ITE_Effect_Type_ApMode_Stop()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xC9
		}

		public void Save_Lighting_Effect_Data(byte save_effect, byte save_light, byte save_speed, byte save_direction, RGBKB_Color save_layout_color, int save_layout_background, string save_layout_alphabet)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x2D
		}

		private unsafe void Save_Lighting_Color_Data(RGBKB_Color save_layout_color)
		{
			((object[])/*Error near IL_0001: Stack underflow*/)[/*Error near IL_0001: Stack underflow*/] = (object)/*Error near IL_0001: Stack underflow*/;
			*(_003F*)(IntPtr)/*Error near IL_0002: Stack underflow*/ = /*Error near IL_0002: Stack underflow*/;
			((IntPtr[])/*Error near IL_0003: Stack underflow*/)[/*Error near IL_0003: Stack underflow*/] = (IntPtr)/*Error near IL_0003: Stack underflow*/;
			/*Error near IL_0003: Unknown opcode: 0xB2*/;
		}

		public bool Set_Lighting_Effect(byte control, byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color, int layout_backgroundcolor = 0, string layout_alphabet = null)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xFD
		}

		public void SingleEffectReset()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x08
		}

		private void ChangeSingleTheme(bool start, byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xDB 0x8C
		}

		private void SetSingleEffect(byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x97 0x46
		}

		private void SetGamingEffect(byte light, byte save, RGB_S[] colorBuffer)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x43 0xE4
		}

		public bool Get_ITE_Light_Value(ref byte light)
		{
			/*Error: Unknown opcode: 0xE1*/;
		}

		private bool Get_LED_Source_Value(ref byte source)
		{
			/*Error near IL_0001: Invalid metadata token*/;
		}

		public bool Set_Welcome_TimeOut_Effect_Enable(bool Enable, byte timeoutEffect, byte timeout)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x5F 0xA3
		}

		public bool Set_Welcome_Effect(byte control, byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color)
		{
			/*Error: Unknown opcode: 0xEF*/;
		}

		private RGBKB_Effect Translate_LM_EffectIndex(byte fw_effect_id)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xD5
		}

		private byte Translate_ITE_EffectIndex(RGBKB_Effect layoutEffect)
		{
			/*Error: Unknown opcode: 0xC8*/;
		}

		private byte Translate_ITE_LightValue(uint layoutLight)
		{
			checked
			{
				_ = (ulong)/*Error near IL_0001: Stack underflow*/;
				/*Error near IL_0001: Unknown opcode: 0xF0*/;
			}
		}

		private byte Translate_ITE_SpeedValue(uint layoutSpeed)
		{
			/*Error: Unknown opcode: 0xFF*/;
		}

		private byte Translate_ITE_DirectionValue(RGBKB_Direction layoutDirection)
		{
			_ = (int)/*Error near IL_0001: Stack underflow*/;
			/*Error near IL_0001: Unknown opcode: 0xEB*/;
		}

		private uint Translate_Layout_LightValue(byte ite_light)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x67 0x93
		}

		public bool ILM_RGBKB_Init(string IsDefaultTool)
		{
			/*Error: Unknown opcode: 0xF6*/;
		}

		public bool ILM_RGBKB_Init()
		{
			//IL_0002: Unknown result type (might be due to invalid IL or missing references)
			//IL_0006: Invalid comparison between I4 and Unknown
			if ((int)((uint[])/*Error near IL_0004: Stack underflow*/)[/*Error near IL_0003: Stack underflow*/ - checked((sbyte)unchecked((int)checked((uint)/*Error near IL_0001: Stack underflow*/)))] >= (int)/*Error near IL_0004: ldloc 63 (out-of-bounds)*/)
			{
				/*Error: Invalid branch target*/;
			}
			/*Error near IL_0007: Read out of bounds.*/;
		}

		bool ILM_RGBKB.ILM_RGBKB_Init()
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_Init
			return this.ILM_RGBKB_Init();
		}

		public bool ILM_RGBLB_Init(string DefaultTool)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xF9
		}

		public bool ILM_RGBLB_Init()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xF9
		}

		public void ILM_RGBKB_SetLightingPower(RGBKB_PowerStatus PowerStatus)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x10
		}

		public bool ILM_RGBKB_SetPower(RGBKB_PowerStatus PowerStatus)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xE4
		}

		bool ILM_RGBKB.ILM_RGBKB_SetPower(RGBKB_PowerStatus PowerStatus)
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetPower
			return this.ILM_RGBKB_SetPower(PowerStatus);
		}

		public void StopMusicTransfer()
		{
			/*Error: Unknown opcode: 0xAC*/;
		}

		public void StartMusicTransfer()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x80
		}

		public bool ILM_RGBKB_GetPower()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x19
		}

		bool ILM_RGBKB.ILM_RGBKB_GetPower()
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetPower
			return this.ILM_RGBKB_GetPower();
		}

		public RGBKB_Type ILM_RGBKB_GetRGBKeyboardType()
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x98
		}

		RGBKB_Type ILM_RGBKB.ILM_RGBKB_GetRGBKeyboardType()
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetRGBKeyboardType
			return this.ILM_RGBKB_GetRGBKeyboardType();
		}

		public string ILM_RGBKB_GetFirmwareVersion()
		{
			/*Error: Empty body found. Decompiled assembly might be a reference assembly.*/;
		}

		string ILM_RGBKB.ILM_RGBKB_GetFirmwareVersion()
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetFirmwareVersion
			return this.ILM_RGBKB_GetFirmwareVersion();
		}

		public bool ILM_RGBKB_SetEffectALL(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, uint layout_light, uint layout_speed, RGBKB_Direction layout_direction, RGBKB_Color layout_color, RGBKB_NV_SAVE layout_save, int layout_backgroundcolor = 0, string layout_alphabet = null)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x23 0xAF
		}

		bool ILM_RGBKB.ILM_RGBKB_SetEffectALL(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, uint layout_light, uint layout_speed, RGBKB_Direction layout_direction, RGBKB_Color layout_color, RGBKB_NV_SAVE layout_save, int layout_backgroundcolor = 0, string layout_alphabet = null)
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetEffectALL
			return this.ILM_RGBKB_SetEffectALL(layout_mode, layout_effect, layout_light, layout_speed, layout_direction, layout_color, layout_save, layout_backgroundcolor, layout_alphabet);
		}

		public bool ILM_RGBKB_GetEffectALL(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect, ref uint layout_light, ref uint layout_speed, ref RGBKB_Direction layout_direction, ref RGBKB_Color layout_color)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xD1
		}

		bool ILM_RGBKB.ILM_RGBKB_GetEffectALL(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect, ref uint layout_light, ref uint layout_speed, ref RGBKB_Direction layout_direction, ref RGBKB_Color layout_color)
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetEffectALL
			return this.ILM_RGBKB_GetEffectALL(layout_mode, ref layout_effect, ref layout_light, ref layout_speed, ref layout_direction, ref layout_color);
		}

		public bool ILM_RGBKB_SetEffect(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xD1
		}

		bool ILM_RGBKB.ILM_RGBKB_SetEffect(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect)
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetEffect
			return this.ILM_RGBKB_SetEffect(layout_mode, layout_effect);
		}

		public bool ILM_RGBKB_GetEffect(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x5D
		}

		bool ILM_RGBKB.ILM_RGBKB_GetEffect(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect)
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetEffect
			return this.ILM_RGBKB_GetEffect(layout_mode, ref layout_effect);
		}

		public bool ILM_RGBKB_SetBrighntess(uint layout_brightness)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xD1
		}

		bool ILM_RGBKB.ILM_RGBKB_SetBrighntess(uint layout_brightness)
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetBrighntess
			return this.ILM_RGBKB_SetBrighntess(layout_brightness);
		}

		public bool ILM_RGBKB_GetBrighntess(ref uint layout_brightness)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0x07 0xA1
		}

		bool ILM_RGBKB.ILM_RGBKB_GetBrighntess(ref uint layout_brightness)
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetBrighntess
			return this.ILM_RGBKB_GetBrighntess(ref layout_brightness);
		}

		public bool ILM_RGBKB_SetSpeed(uint layout_speed)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xD1
		}

		bool ILM_RGBKB.ILM_RGBKB_SetSpeed(uint layout_speed)
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetSpeed
			return this.ILM_RGBKB_SetSpeed(layout_speed);
		}

		public unsafe bool ILM_RGBKB_SetColor(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, RGBKB_Color layout_color)
		{
			//IL_0000: Unknown result type (might be due to invalid IL or missing references)
			//IL_0005: Invalid comparison between Unknown and I4
			_ = /*Error near IL_0001: Stack underflow*/>> (int)/*Error near IL_0001: Stack underflow*/;
			/*Error near IL_0001: stloc 166 (out-of-bounds)*/;
			/*Error near IL_0003: stloc 3 (out-of-bounds)*/;
			if ((int)/*Error near IL_000a: Stack underflow*/ <= (int)(*(sbyte*)(IntPtr)/*Error near IL_0005: Stack underflow*/))
			{
				/*Error: Invalid branch target*/;
			}
			return (byte)/*Error near IL_000b: Stack underflow*/ != 0;
		}

		bool ILM_RGBKB.ILM_RGBKB_SetColor(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, RGBKB_Color layout_color)
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetColor
			return this.ILM_RGBKB_SetColor(layout_mode, layout_effect, layout_color);
		}

		public bool ILM_RGBKB_SaveLightingLevel(uint layout_light)
		{
		//Invalid MethodBodyBlock: Invalid method header: 0xFF 0x75
		}

		bool ILM_RGBKB.ILM_RGBKB_SaveLightingLevel(uint layout_light)
		{
			//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SaveLightingLevel
			return this.ILM_RGBKB_SaveLightingLevel(layout_light);
		}
	}
}
