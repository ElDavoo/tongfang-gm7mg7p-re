using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Media;
using Define;
using GCUService.MyRgbKeyboard;
using LightingModel;
using MyECIO;
using Utility;

namespace MyControlCenter.MyRgbKeyboard;

public class HIDKeyboard : IDisposable
{
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

	internal const byte EFFECT_THINKING = 33;

	internal const byte EFFECT_MUSIC = 34;

	internal const byte EFFECT_USERMODE = 51;

	internal const byte EFFECT_UNKNOWN = byte.MaxValue;

	internal const byte EFFECT_STARTSPARK = 24;

	internal const byte EFFECT_STARTCOLLISION = 25;

	internal const byte EFFECT_MANUAL = 64;

	internal const byte EFFECT_BATTERYPERCENT = 35;

	internal object _powerLock = new object();

	internal object _brightnessLock = new object();

	private string _FWVersion;

	internal RGBKB_Mode _Mode;

	internal string _SaveDCLight = "DCLight";

	internal string _SaveACLight = "ACLight";

	internal string _SavePowerSwich = "PowerSwitch";

	internal const string _SaveLastEffect = "LastEffect";

	internal const string _SaveLastWelcomeEffect = "LastWelcomeEffect";

	internal LM_ITE_RGB _KeyboardControl;

	internal LM_EC_RGB _EcKeyboardControl;

	internal RGBKB_PowerStatus _PowerStatus;

	internal bool _NightModSwitch;

	internal RGB_S _LastNightModeColor = new RGB_S(0u, 0, 0, 0);

	internal byte _LastEffectRun;

	internal SAVE_LIGHTING_EFFECT_DATA _EffectData;

	internal SAVE_LIGHTING_EFFECT_DATA _WelcomeEffectData;

	internal RGBKB_PowerMode CurrentPowerMode;

	internal uint _DC_LightLevel;

	internal uint _AC_LightLevel = 3u;

	private bool _firstApStart = true;

	private bool _AllPowerAnimation;

	internal bool _CloseAnimation = true;

	private bool _OpenAnimation;

	internal const ushort EC_RGBKBBKL_LEVEL_UPDATE = 240;

	internal const ushort EC_RGBKBBKL_LEVEL_DOWN = 177;

	internal const ushort EC_RGBKBBKL_LEVEL_UP = 178;

	internal const ushort EC_RGBKBBKL_CIRCLE_UP = 185;

	internal const ushort EC_ChinaMode_Change = 182;

	internal const ushort EC_SINGLEKBL_LEVEL_CHG = 180;

	private KeyboardCloseTimer keyboardcloseTimer = KeyboardCloseTimer.CreateInstance;

	private uint beforeBrightness;

	internal List<byte> _APEffectList = new List<byte> { 21, 12, 13, 15, 23 };

	internal List<byte> _UserModeEffectList = new List<byte> { 12, 13, 15, 23, 34 };

	internal bool _InitIsDone;

	private object _nightModeLock = new object();

	internal bool _BeforeNightIsZero;

	private bool disposed;

	public event RGBKB_Event_Handler m_Layout_Event_handler;

	public HIDKeyboard(LM_Manager lm_Manager, string fWVersion)
	{
		_FWVersion = fWVersion;
		if (lm_Manager.m_KB_Solution == RGBKB_Solution.ITE)
		{
			_KeyboardControl = (LM_ITE_RGB)lm_Manager.GetITE_RGB();
		}
		else if (lm_Manager.m_KB_Solution == RGBKB_Solution.EC)
		{
			_EcKeyboardControl = (LM_EC_RGB)lm_Manager.GetEC_RGB();
		}
		SettingsStorageExtensions.CheckingDir();
		keyboardcloseTimer.ControlBrigtnessEvent -= KeyboardcloseTimer_ControlBrigtnessEvent;
		keyboardcloseTimer.ControlBrigtnessEvent += KeyboardcloseTimer_ControlBrigtnessEvent;
	}

	internal RGBKB_Color ConvertJsonRGB2RGBColor(dynamic color)
	{
		bool bCircular = color["isCircular"];
		uint num = color["ColorBlocks"];
		RGBKB_Color result = new RGBKB_Color(bCircular, num);
		for (int i = 0; i < num; i++)
		{
			result.ColorBuffer[i].ID = color["ColorBuffer"][i]["ID"];
			result.ColorBuffer[i].R = color["ColorBuffer"][i]["R"];
			result.ColorBuffer[i].G = color["ColorBuffer"][i]["G"];
			result.ColorBuffer[i].B = color["ColorBuffer"][i]["B"];
		}
		return result;
	}

	internal virtual byte Translate_ITE_EffectIndex(RGBKB_Effect layoutEffect)
	{
		return layoutEffect switch
		{
			RGBKB_Effect.Single => 1, 
			RGBKB_Effect.Breathing => 2, 
			RGBKB_Effect.Wave => 3, 
			RGBKB_Effect.Reactive => 4, 
			RGBKB_Effect.Rainbow => 5, 
			RGBKB_Effect.Ripple => 6, 
			RGBKB_Effect.RippleO => 22, 
			RGBKB_Effect.Marquee => 9, 
			RGBKB_Effect.Raindrop => 10, 
			RGBKB_Effect.Spark => 17, 
			RGBKB_Effect.Aurora => 14, 
			RGBKB_Effect.UserMode => 51, 
			RGBKB_Effect.Music => 34, 
			RGBKB_Effect.Flash => 18, 
			RGBKB_Effect.Mix => 19, 
			RGBKB_Effect.Neon => 15, 
			RGBKB_Effect.Stack => 12, 
			RGBKB_Effect.Impact => 13, 
			RGBKB_Effect.Gaming => 21, 
			RGBKB_Effect.Alphabet => 23, 
			RGBKB_Effect.StarHitting => 25, 
			RGBKB_Effect.StarSpark => 24, 
			RGBKB_Effect.Thinking => 33, 
			RGBKB_Effect.Manual => 64, 
			RGBKB_Effect.BatteryPercent => 35, 
			_ => byte.MaxValue, 
		};
	}

	internal virtual byte Translate_ITE_LightValue(uint layoutLight)
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

	internal virtual byte Translate_ITE_SpeedValue(uint layoutSpeed)
	{
		return layoutSpeed switch
		{
			0u => 10, 
			1u => 7, 
			2u => 5, 
			3u => 3, 
			4u => 1, 
			_ => 1, 
		};
	}

	internal byte Translate_ITE_DirectionValue(RGBKB_Direction layoutDirection)
	{
		return layoutDirection switch
		{
			RGBKB_Direction.None => 0, 
			RGBKB_Direction.LeftRight => 1, 
			RGBKB_Direction.RightLeft => 2, 
			RGBKB_Direction.DownUp => 3, 
			RGBKB_Direction.UpDown => 4, 
			RGBKB_Direction.OnKeyPressed => 1, 
			RGBKB_Direction.Sync => 3, 
			_ => 1, 
		};
	}

	internal virtual uint Translate_Layout_LightValue(byte ite_light)
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

	internal RGB_S BackgroundColorConverter(int colorindex)
	{
		RGB_S result = new RGB_S
		{
			ID = 0u,
			R = 0,
			G = 0,
			B = 0
		};
		switch (colorindex)
		{
		case 1:
			result.R = 3;
			break;
		case 2:
			result.R = 9;
			result.G = 1;
			break;
		case 3:
			result.R = 9;
			result.G = 3;
			break;
		case 4:
			result.G = 1;
			break;
		case 5:
			result.G = 1;
			result.B = 1;
			break;
		case 6:
			result.B = 1;
			break;
		case 7:
			result.R = 3;
			result.B = 2;
			break;
		case 8:
			result.R = 1;
			result.G = 1;
			result.B = 1;
			break;
		}
		return result;
	}

	internal byte GetEffectType(byte save_effect)
	{
		byte b = 0;
		byte b2 = 1;
		byte b3 = 3;
		byte result = 4;
		if (_APEffectList.Contains(save_effect))
		{
			return result;
		}
		return save_effect switch
		{
			51 => b2, 
			34 => b3, 
			_ => b, 
		};
	}

	public bool GetInitSuccessful()
	{
		return _InitIsDone;
	}

	public void SetACDCLightString(string PowerSwitchString, string ACLightString, string DCLightString)
	{
		_SavePowerSwich = PowerSwitchString;
		_SaveACLight = ACLightString;
		_SaveDCLight = DCLightString;
	}

	public virtual async void InitalizeKeyboardEffect(bool unplug = false)
	{
		_ = 3;
		try
		{
			uint aclevel = await SettingsStorageExtensions.ReadAsync<uint>("", _SaveACLight);
			uint dclevel = await SettingsStorageExtensions.ReadAsync<uint>("", _SaveDCLight);
			RGBKB_PowerStatus rGBKB_PowerStatus = await SettingsStorageExtensions.ReadAsync<RGBKB_PowerStatus>("", _SavePowerSwich);
			LogCtrl.Write("Init HID Device powerstatus : " + rGBKB_PowerStatus);
			int projectID = _KeyboardControl.GetProjectID();
			string text = projectID.ToString();
			LogCtrl.Write("Init HID Device projectid : " + text);
			if (projectID >= Convert.ToInt32(ProjectID.IDP) && _KeyboardControl.ILM_RGBKB_GetRGBKeyboardType() == RGBKB_Type.SingleZone)
			{
				bool flag = MyEcCtrl.Instance.IsChinaMode();
				LogCtrl.Write("China Mode Stauts : " + flag);
				if (rGBKB_PowerStatus == RGBKB_PowerStatus.On && !flag)
				{
					SetPowerStatus(RGBKB_PowerStatus.Off);
				}
				else
				{
					_PowerStatus = rGBKB_PowerStatus;
					SetPowerStatus(_PowerStatus);
				}
			}
			else
			{
				LogCtrl.Write("China Mode Stauts : no support");
				_PowerStatus = rGBKB_PowerStatus;
				SetPowerStatus(_PowerStatus);
			}
			LogCtrl.Write("After China Mode PoserStatus : " + rGBKB_PowerStatus);
			SAVE_LIGHTING_EFFECT_DATA effectData = await SettingsStorageExtensions.ReadAsync<SAVE_LIGHTING_EFFECT_DATA>(_KeyboardControl?.ILM_RGBKB_GetRGBKeyboardType().ToString(), text + "_LastEffect");
			if (effectData.save_effect == 0)
			{
				List<Color> obj = new List<Color>
				{
					Color.FromArgb(byte.MaxValue, byte.MaxValue, 0, 0),
					Color.FromArgb(byte.MaxValue, byte.MaxValue, 165, 0),
					Color.FromArgb(byte.MaxValue, byte.MaxValue, byte.MaxValue, 0),
					Color.FromArgb(byte.MaxValue, 0, byte.MaxValue, 0),
					Color.FromArgb(byte.MaxValue, 0, 0, byte.MaxValue),
					Color.FromArgb(byte.MaxValue, 0, byte.MaxValue, byte.MaxValue),
					Color.FromArgb(byte.MaxValue, 139, 0, byte.MaxValue)
				};
				RGBKB_Color save_layout_color = new RGBKB_Color(bCircular: false, 7u);
				int num = 0;
				foreach (Color item in obj)
				{
					save_layout_color.ColorBuffer[num].ID = (uint)num;
					save_layout_color.ColorBuffer[num].R = item.R;
					save_layout_color.ColorBuffer[num].G = item.G;
					save_layout_color.ColorBuffer[num].B = item.B;
					num++;
				}
				_EffectData.save_mode = RGBKB_Mode.Lighting;
				_EffectData.save_effect = Translate_ITE_EffectIndex(RGBKB_Effect.Rainbow);
				_EffectData.save_light = Translate_ITE_LightValue(3u);
				_EffectData.save_speed = Translate_ITE_SpeedValue(2u);
				_EffectData.save_direction = Translate_ITE_DirectionValue(RGBKB_Direction.LeftRight);
				_EffectData.save_layout_color = save_layout_color;
				SaveEffectData();
			}
			else
			{
				_EffectData = effectData;
			}
			SetACDCLight(unplug, aclevel, dclevel);
			if (_EffectData.save_effect != 0)
			{
				RunEffct(0);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("exception: " + ex, "InitalizeKeyboardEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\HIDKeyboard.cs", 452);
		}
	}

	internal virtual void SetACDCLight(bool unplug, uint aclevel, uint dclevel)
	{
		_DC_LightLevel = dclevel;
		_AC_LightLevel = aclevel;
		if (unplug)
		{
			CurrentPowerMode = RGBKB_PowerMode.DC;
			SetBrightnessStrategy(Translate_ITE_LightValue(dclevel));
			_EffectData.save_light = Translate_ITE_LightValue(dclevel);
			SaveEffectData();
			LogCtrl.Write("In DC Mode Backlight Now bcaklight : " + _EffectData.save_light);
		}
		else
		{
			CurrentPowerMode = RGBKB_PowerMode.AC;
			SetBrightnessStrategy(Translate_ITE_LightValue(aclevel));
			_EffectData.save_light = Translate_ITE_LightValue(aclevel);
			SaveEffectData();
			LogCtrl.Write("In AC Mode Backlight Now bcaklight : " + _EffectData.save_light);
		}
	}

	private void _88Htest()
	{
		byte Control = 0;
		byte Effect = 0;
		byte Speed = 0;
		byte ColorIndex = 0;
		byte Direction = 0;
		byte Light = 0;
		_KeyboardControl?.HID_Get_Effect_Type_88H(ref Control, ref Effect, ref Speed, ref Light, ref ColorIndex, ref Direction);
	}

	public virtual void AsyncWelcome()
	{
		try
		{
			List<string[]> keyboardWelcomeEffect = NvramVariable.GetKeyboardWelcomeEffect();
			LogCtrl.TraceMessage("data[0]: " + string.Join(",", keyboardWelcomeEffect[0]), "AsyncWelcome", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\HIDKeyboard.cs", 501);
			LogCtrl.TraceMessage("data[1]: " + string.Join(",", keyboardWelcomeEffect[1]), "AsyncWelcome", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\HIDKeyboard.cs", 502);
			SAVE_LIGHTING_EFFECT_DATA welcomeEffectData = default(SAVE_LIGHTING_EFFECT_DATA);
			RGBKB_PowerStatus rGBKB_PowerStatus = RGBKB_PowerStatus.On;
			if (Convert.ToByte(keyboardWelcomeEffect[0][0]) != byte.MaxValue)
			{
				welcomeEffectData.save_effect = Convert.ToByte(Convert.ToUInt32(keyboardWelcomeEffect[0][2], 16));
				welcomeEffectData.save_speed = Convert.ToByte(Convert.ToUInt32(keyboardWelcomeEffect[0][3], 16));
				welcomeEffectData.save_light = Convert.ToByte(Convert.ToUInt32(keyboardWelcomeEffect[0][4], 16));
				welcomeEffectData.save_direction = Convert.ToByte(Convert.ToUInt32(keyboardWelcomeEffect[0][5], 16));
				rGBKB_PowerStatus = (Convert.ToBoolean(Convert.ToUInt32(keyboardWelcomeEffect[1][2], 16)) ? RGBKB_PowerStatus.On : RGBKB_PowerStatus.Off);
				_WelcomeEffectData = welcomeEffectData;
				SetPowerStatus(rGBKB_PowerStatus);
			}
		}
		catch (Exception)
		{
		}
	}

	public virtual async void InitalizeWelcomeKeyboardEffect(RGBKB_PowerStatus power, bool IsAppExists, bool unplug = false)
	{
		try
		{
			string text = _KeyboardControl.GetProjectID().ToString();
			SAVE_LIGHTING_EFFECT_DATA welcomeEffectData = await SettingsStorageExtensions.ReadAsync<SAVE_LIGHTING_EFFECT_DATA>(_KeyboardControl?.ILM_RGBKB_GetRGBKeyboardType().ToString(), text + "_LastWelcomeEffect");
			if (welcomeEffectData.save_effect != 0)
			{
				_WelcomeEffectData = welcomeEffectData;
				_KeyboardControl?.Set_Welcome_Effect(3, _WelcomeEffectData.save_effect, _WelcomeEffectData.save_light, _WelcomeEffectData.save_speed, _WelcomeEffectData.save_direction, Translate_ITE_LightValue(_DC_LightLevel), _WelcomeEffectData.save_layout_color);
				SaveWelcomeEffectData();
				LogCtrl.Write("Set_Welcome_TimeOut_Effect_Enable");
				if (IsAppExists)
				{
					if (power.Equals(RGBKB_PowerStatus.On))
					{
						_KeyboardControl?.Set_Welcome_TimeOut_Effect_Enable(Enable: true, _WelcomeEffectData.save_effect, 4);
					}
					else
					{
						_KeyboardControl?.Set_Welcome_TimeOut_Effect_Enable(Enable: false, _WelcomeEffectData.save_effect, 0);
					}
				}
				else if (power.Equals(RGBKB_PowerStatus.On))
				{
					_KeyboardControl?.Set_Welcome_TimeOut_Effect_Enable(Enable: true, _WelcomeEffectData.save_effect, 4);
				}
				else
				{
					_KeyboardControl?.Set_Welcome_TimeOut_Effect_Enable(Enable: false, _WelcomeEffectData.save_effect, 0);
				}
			}
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
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("exception: " + ex, "InitalizeWelcomeKeyboardEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\HIDKeyboard.cs", 625);
		}
	}

	internal virtual void SaveEffectData()
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

	internal async void SaveWelcomeEffectData()
	{
		string text = _KeyboardControl?.GetProjectID().ToString();
		SettingsStorageExtensions.SaveAsync(_KeyboardControl?.ILM_RGBKB_GetRGBKeyboardType().ToString(), text + "_LastWelcomeEffect", _WelcomeEffectData);
	}

	internal async void SavePowerStatus()
	{
		SettingsStorageExtensions.SaveAsync("", _SavePowerSwich, _PowerStatus);
	}

	public void SetMode(RGBKB_Mode mode)
	{
		_Mode = mode;
	}

	public virtual bool SetEffect(dynamic data)
	{
		RGBKB_Mode save_mode = data["mode"];
		RGBKB_Effect layoutEffect = data["effect"];
		uint layoutLight = data["light"];
		uint layoutSpeed = data["speed"];
		RGBKB_Direction layoutDirection = RGBKB_Direction.None;
		RGBKB_NV_SAVE rGBKB_NV_SAVE = RGBKB_NV_SAVE.NOT_SAVE;
		if (data["direction"] != null)
		{
			layoutDirection = data["direction"];
		}
		if (data["nv_save"] != null)
		{
			rGBKB_NV_SAVE = data["nv_save"];
		}
		RGBKB_Color save_layout_color = ConvertJsonRGB2RGBColor(data["color"]);
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

	public virtual bool SetWelcomeEffect(dynamic data)
	{
		RGBKB_Mode save_mode = data["mode"];
		RGBKB_Effect layoutEffect = data["effect"];
		uint layoutLight = data["light"];
		uint layoutSpeed = data["speed"];
		RGBKB_Direction layoutDirection = data["direction"];
		RGBKB_Color save_layout_color = ConvertJsonRGB2RGBColor(data["color"]);
		_ = (RGBKB_NV_SAVE)data["nv_save"];
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
			save_layout_alphbet = save_layout_alphbet,
			save_layout_backgroundcolor = save_layout_backgroundcolor
		};
		if (_WelcomeEffectData.Equals(sAVE_LIGHTING_EFFECT_DATA))
		{
			return false;
		}
		_EffectData.save_light = sAVE_LIGHTING_EFFECT_DATA.save_light;
		_WelcomeEffectData = sAVE_LIGHTING_EFFECT_DATA;
		if (CurrentPowerMode == RGBKB_PowerMode.DC)
		{
			_DC_LightLevel = Translate_Layout_LightValue(_EffectData.save_light);
		}
		else
		{
			_AC_LightLevel = Translate_Layout_LightValue(_EffectData.save_light);
		}
		SaveWelcomeEffectData();
		return true;
	}

	public virtual void SetPowerStatus(RGBKB_PowerStatus powerstatus)
	{
		_PowerStatus = powerstatus;
		if (!_PowerStatus.Equals(RGBKB_PowerStatus.On))
		{
			_KeyboardControl?.ILM_RGBKB_SetPower(powerstatus);
			_KeyboardControl?.Set_Welcome_TimeOut_Effect_Enable(Enable: false, _WelcomeEffectData.save_effect, 0);
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
				_KeyboardControl?.ILM_RGBKB_SetPower(powerstatus);
				_KeyboardControl?.Set_Welcome_TimeOut_Effect_Enable(Enable: true, _WelcomeEffectData.save_effect, 4);
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

	public RGBKB_PowerStatus GetPowerStatus()
	{
		if (Monitor.TryEnter(_powerLock, 1500))
		{
			try
			{
				return _PowerStatus;
			}
			finally
			{
				Monitor.Exit(_powerLock);
			}
		}
		return RGBKB_PowerStatus.Off;
	}

	public string GetWelcomeStatus()
	{
		string text = null;
		switch (_WelcomeEffectData.save_effect)
		{
		case 1:
			text = RGBKB_Effect.Single.ToString();
			break;
		case 2:
			text = RGBKB_Effect.Breathing.ToString();
			break;
		case 4:
			text = RGBKB_Effect.Reactive.ToString();
			break;
		case 3:
			text = RGBKB_Effect.Wave.ToString();
			break;
		case 5:
			text = RGBKB_Effect.Rainbow.ToString();
			break;
		case 6:
			text = RGBKB_Effect.Ripple.ToString();
			break;
		case 9:
			text = RGBKB_Effect.Marquee.ToString();
			break;
		case 10:
			text = RGBKB_Effect.Raindrop.ToString();
			break;
		case 14:
			text = RGBKB_Effect.Aurora.ToString();
			break;
		case 21:
			text = RGBKB_Effect.Gaming.ToString();
			break;
		case 19:
			text = RGBKB_Effect.Mix.ToString();
			break;
		case 18:
			text = RGBKB_Effect.Flash.ToString();
			break;
		case 13:
			text = RGBKB_Effect.Impact.ToString();
			break;
		case 33:
			text = RGBKB_Effect.Thinking.ToString();
			break;
		}
		LogCtrl.Write("KeyboardType: " + _KeyboardControl?.ILM_RGBKB_GetRGBKeyboardType().ToString() + ", Welcome Effect : " + text);
		return text;
	}

	public string GetWelcomeDirectionStatus()
	{
		string text = null;
		if (_WelcomeEffectData.save_direction == 0)
		{
			text = RGBKB_Direction.LeftRight.ToString();
		}
		else if (_WelcomeEffectData.save_direction == 2)
		{
			text = RGBKB_Direction.DownUp.ToString();
		}
		else if (_WelcomeEffectData.save_direction == 3)
		{
			text = RGBKB_Direction.RightLeft.ToString();
		}
		else if (_WelcomeEffectData.save_direction == 4)
		{
			text = RGBKB_Direction.UpDown.ToString();
		}
		LogCtrl.Write("Welcome direction : " + text);
		return text;
	}

	internal void NightPowerSwitch(bool NightPower)
	{
		Task.Run(delegate
		{
			if (Monitor.TryEnter(_nightModeLock, 200))
			{
				try
				{
					if (NightPower)
					{
						RGB_S lastNightModeColor = BackgroundColorConverter(_EffectData.save_layout_backgroundcolor);
						_KeyboardControl?.HID_Set_Effect_Type_08H(4, 0, lastNightModeColor.R, lastNightModeColor.G, lastNightModeColor.B, 0, 0);
						_LastNightModeColor = lastNightModeColor;
					}
					else
					{
						_KeyboardControl?.HID_Set_Effect_Type_08H(5, 0, 0, 0, 0, 0, 0);
						_LastNightModeColor = new RGB_S
						{
							R = 0,
							G = 0,
							B = 0
						};
					}
				}
				finally
				{
					Monitor.Exit(_nightModeLock);
				}
			}
		});
	}

	protected virtual void ScanCodeUpdatedBrightness(RGBKB_Event_Data event_data)
	{
		if (this.m_Layout_Event_handler != null)
		{
			this.m_Layout_Event_handler(event_data);
		}
	}

	public void SetChinaMode(int scancode)
	{
		if (scancode == 182)
		{
			if (MyEcCtrl.Instance.IsChinaMode())
			{
				SetPowerStatus(RGBKB_PowerStatus.On);
			}
			else
			{
				SetPowerStatus(RGBKB_PowerStatus.Off);
			}
		}
	}

	public virtual void SetBrinessByScanCode(int scancode)
	{
		switch (scancode)
		{
		case 177:
		case 178:
		{
			LogCtrl.Write("HID_Default B1 B2 : scan code: " + scancode);
			if (_PowerStatus.Equals(RGBKB_PowerStatus.Off))
			{
				LogCtrl.Write("Scan code open power");
				_PowerStatus = RGBKB_PowerStatus.On;
				SavePowerStatus();
				RunEffct(0);
			}
			uint num2 = Translate_Layout_LightValue(_EffectData.save_light);
			bool flag = true;
			switch (scancode)
			{
			case 177:
				num2 = ((num2 != 0) ? (num2 - 1) : 0u);
				break;
			case 178:
				if (num2 + 1 > 4)
				{
					num2 = 4u;
					flag = false;
				}
				else
				{
					num2++;
				}
				break;
			}
			_EffectData.save_light = Translate_ITE_LightValue(num2);
			if (flag)
			{
				LogCtrl.Write("2ND in scancode support 09h : " + _EffectData.save_light);
				SetBrightnessStrategy(_EffectData.save_light);
			}
			RGBKB_Event_Data event_data2 = new RGBKB_Event_Data
			{
				event_id = RGBKB_EventID.Brightness_update,
				envet_data_len = 1u,
				event_data = new byte[1]
			};
			event_data2.event_data[0] = (byte)Translate_Layout_LightValue(_EffectData.save_light);
			AsyncBrignessToEC(_EffectData.save_light);
			ScanCodeUpdatedBrightness(event_data2);
			break;
		}
		case 240:
			try
			{
				LogCtrl.Write("HID_Default FO : scan code: " + scancode);
				if (_PowerStatus.Equals(RGBKB_PowerStatus.Off))
				{
					_PowerStatus = RGBKB_PowerStatus.On;
					SavePowerStatus();
					RunEffct(0);
				}
				byte fWLight = GetFWLight();
				if (_firstApStart)
				{
					_EffectData.save_light = fWLight;
					SetBrightnessStrategy(fWLight);
					RunEffct(0);
					_firstApStart = false;
				}
				else
				{
					_EffectData.save_light = fWLight;
					SetBrightnessStrategy(fWLight);
				}
				RGBKB_Event_Data event_data3 = new RGBKB_Event_Data
				{
					event_id = RGBKB_EventID.Brightness_update,
					envet_data_len = 1u,
					event_data = new byte[1]
				};
				event_data3.event_data[0] = (byte)Translate_Layout_LightValue(fWLight);
				ScanCodeUpdatedBrightness(event_data3);
				Thread.Sleep(50);
				break;
			}
			catch (Exception)
			{
				break;
			}
		case 185:
		{
			LogCtrl.Write("HID_Default Circle B9 : scan code: " + scancode);
			if (_PowerStatus.Equals(RGBKB_PowerStatus.Off))
			{
				LogCtrl.Write("Scan code open power");
				_PowerStatus = RGBKB_PowerStatus.On;
				SavePowerStatus();
				RunEffct(0);
			}
			uint num = Translate_Layout_LightValue(_EffectData.save_light);
			num = (num + 1) % 5;
			_EffectData.save_light = Translate_ITE_LightValue(num);
			SetBrightnessStrategy(_EffectData.save_light);
			RGBKB_Event_Data event_data = new RGBKB_Event_Data
			{
				event_id = RGBKB_EventID.Brightness_update,
				envet_data_len = 1u,
				event_data = new byte[1]
			};
			event_data.event_data[0] = (byte)Translate_Layout_LightValue(_EffectData.save_light);
			AsyncBrignessToEC(_EffectData.save_light);
			ScanCodeUpdatedBrightness(event_data);
			break;
		}
		}
	}

	private byte GetFWLight()
	{
		byte light = 0;
		uint num = 0u;
		while (true)
		{
			_KeyboardControl?.Get_ITE_Light_Value(ref light);
			if (light == _EffectData.save_light || (light != 1 && light != _EffectData.save_light) || num >= 5)
			{
				break;
			}
			Thread.Sleep(100);
			num++;
		}
		return light;
	}

	public virtual void UnPlugged()
	{
		byte brightness = Translate_ITE_LightValue(_DC_LightLevel);
		CurrentPowerMode = RGBKB_PowerMode.DC;
		PluggedSetBrightness(brightness);
		LM_ITE_RGB keyboardControl = _KeyboardControl;
		if (keyboardControl != null && keyboardControl.ILM_RGBKB_GetRGBKeyboardType() == RGBKB_Type.FourZone && _EffectData.save_effect == 34)
		{
			_KeyboardControl?.StopMusicTransfer();
		}
	}

	public virtual void Plugged()
	{
		byte brightness = Translate_ITE_LightValue(_AC_LightLevel);
		CurrentPowerMode = RGBKB_PowerMode.AC;
		PluggedSetBrightness(brightness);
		LM_ITE_RGB keyboardControl = _KeyboardControl;
		if (keyboardControl != null && keyboardControl.ILM_RGBKB_GetRGBKeyboardType() == RGBKB_Type.FourZone && _EffectData.save_effect == 34)
		{
			RunEffct(0);
		}
	}

	internal virtual void PluggedSetBrightness(uint brightness)
	{
		try
		{
			SetBrightnessStrategy((byte)brightness);
			_EffectData.save_light = (byte)brightness;
			RGBKB_Event_Data event_data = new RGBKB_Event_Data
			{
				event_id = RGBKB_EventID.Brightness_update,
				envet_data_len = 2u,
				event_data = new byte[2]
			};
			event_data.event_data[0] = (byte)Translate_Layout_LightValue(_EffectData.save_light);
			event_data.event_data[1] = 2;
			ScanCodeUpdatedBrightness(event_data);
		}
		catch (Exception)
		{
		}
	}

	private void KeyboardcloseTimer_ControlBrigtnessEvent(object sender, EventArgs e)
	{
		if (CheckAurora.Instance.GetAuroraStauts())
		{
			return;
		}
		if (Convert.ToBoolean(sender))
		{
			beforeBrightness = GetBrightness();
			LM_ITE_RGB keyboardControl = _KeyboardControl;
			if (keyboardControl != null && keyboardControl.ILM_RGBKB_GetRGBKeyboardType() == RGBKB_Type.FourZone && _EffectData.save_effect == 34)
			{
				_KeyboardControl?.StopMusicTransfer();
			}
			new Thread((ThreadStart)delegate
			{
				CloseAnimation();
			}).Start();
			return;
		}
		if (_EffectData.save_effect != 51)
		{
			Task.Run(delegate
			{
				RunEffct(0);
				LogCtrl.Write((_KeyboardControl?.ILM_RGBKB_GetRGBKeyboardType()).ToString() + " CloseTimer ee");
			});
		}
		else
		{
			RunEffct(0);
			LogCtrl.Write((_KeyboardControl?.ILM_RGBKB_GetRGBKeyboardType()).ToString() + " CloseTimer usermode ee");
		}
		LM_ITE_RGB keyboardControl2 = _KeyboardControl;
		if (keyboardControl2 != null && keyboardControl2.ILM_RGBKB_GetRGBKeyboardType() == RGBKB_Type.FourZone && _EffectData.save_effect == 34)
		{
			_KeyboardControl?.StartMusicTransfer();
		}
	}

	public virtual void SetBrightness(uint level)
	{
		try
		{
			_EffectData.save_light = Translate_ITE_LightValue(level);
			SetBrightnessStrategy(_EffectData.save_light);
			AsyncBrignessToEC(_EffectData.save_light);
		}
		catch (Exception)
		{
		}
	}

	private void AsyncBrignessToEC(byte brightness)
	{
		byte Data = 0;
		MyEcCtrl.Instance.Read("HIDKeyboard", 1932, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		switch (brightness)
		{
		case 0:
			bitArray[5] = false;
			bitArray[6] = false;
			bitArray[7] = false;
			break;
		case 8:
			bitArray[5] = true;
			bitArray[6] = false;
			bitArray[7] = false;
			break;
		case 22:
			bitArray[5] = false;
			bitArray[6] = true;
			bitArray[7] = false;
			break;
		case 36:
			bitArray[5] = true;
			bitArray[6] = true;
			bitArray[7] = false;
			break;
		case 50:
			bitArray[5] = false;
			bitArray[6] = false;
			bitArray[7] = true;
			break;
		}
		byte data = ConvertToByte(bitArray);
		MyEcCtrl.Instance.Write("HIDKeyboard", 1932, data);
	}

	internal byte ConvertToByte(BitArray bits)
	{
		_ = bits.Count;
		_ = 8;
		byte[] array = new byte[1];
		bits.CopyTo(array, 0);
		return array[0];
	}

	public virtual uint GetBrightness()
	{
		return Translate_Layout_LightValue(_EffectData.save_light);
	}

	public virtual void SetBrightness_ACDC(uint ACBrightness, uint DCBrighteness, bool saveACDC = true)
	{
	}

	internal virtual void SetBrightnessStrategy(byte brightness, bool saveACDC = true)
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
			SaveEffectData();
		}
		if (_Mode.Equals(RGBKB_Mode.Night))
		{
			if (brightness < 8)
			{
				_BeforeNightIsZero = true;
				_KeyboardControl?.ILM_RGBKB_SetLightingPower(RGBKB_PowerStatus.Off);
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
				_KeyboardControl?.Set_Lighting_Effect(4, _EffectData.save_effect, brightness, _EffectData.save_speed, _EffectData.save_direction, 0, _EffectData.save_layout_color, _EffectData.save_layout_backgroundcolor, _EffectData.save_layout_alphbet);
			}
			else
			{
				_KeyboardControl?.HID_Set_Brightness_Level_09H(brightness);
			}
			_BeforeNightIsZero = false;
		}
		else
		{
			_KeyboardControl?.HID_Set_Brightness_Level_09H(brightness);
		}
	}

	public virtual void RunWelcomeEffect()
	{
		if (_PowerStatus.Equals(RGBKB_PowerStatus.On) && _Mode == RGBKB_Mode.Welcome)
		{
			_KeyboardControl?.Set_Welcome_Effect(3, _WelcomeEffectData.save_effect, _WelcomeEffectData.save_light, _WelcomeEffectData.save_speed, _WelcomeEffectData.save_direction, Translate_ITE_LightValue(_DC_LightLevel), _WelcomeEffectData.save_layout_color);
			if (_EffectData.save_effect != 0)
			{
				RunEffct(1);
			}
		}
	}

	internal void NightModeReflash(RGBKB_Mode mode)
	{
		if (mode.Equals(RGBKB_Mode.Night))
		{
			NightPowerSwitch(NightPower: true);
			_NightModSwitch = true;
			return;
		}
		if (_NightModSwitch)
		{
			NightPowerSwitch(NightPower: false);
		}
		_NightModSwitch = false;
	}

	public virtual void RunEffct(byte SAVED = 0)
	{
		if (CheckAurora.Instance.GetAuroraStauts())
		{
			return;
		}
		try
		{
			if (!_PowerStatus.Equals(RGBKB_PowerStatus.On))
			{
				return;
			}
			LogCtrl.Write("KeyboardType: " + _KeyboardControl?.ILM_RGBKB_GetRGBKeyboardType().ToString() + ", Run Effect in " + _EffectData.save_effect);
			if (_EffectData.save_mode == RGBKB_Mode.Lighting)
			{
				_KeyboardControl.m_effect_type = GetEffectType(_EffectData.save_effect);
				_KeyboardControl.ChangeEffect = ((_LastEffectRun != _EffectData.save_effect) ? true : false);
				NightModeReflash(_EffectData.save_mode);
				if (_AllPowerAnimation)
				{
					Task.Run(delegate
					{
						_KeyboardControl?.Set_Lighting_Effect(2, _EffectData.save_effect, 0, _EffectData.save_speed, _EffectData.save_direction, SAVED, _EffectData.save_layout_color, 0, _EffectData.save_layout_alphbet);
					}).ContinueWith(delegate
					{
						OpenAnimation();
					});
				}
				else
				{
					_KeyboardControl?.Set_Lighting_Effect(2, _EffectData.save_effect, _EffectData.save_light, _EffectData.save_speed, _EffectData.save_direction, SAVED, _EffectData.save_layout_color, 0, _EffectData.save_layout_alphbet);
				}
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
				if (_AllPowerAnimation)
				{
					Task.Run(delegate
					{
						_KeyboardControl?.Set_Lighting_Effect(4, _EffectData.save_effect, 0, _EffectData.save_speed, _EffectData.save_direction, SAVED, _EffectData.save_layout_color, 0, _EffectData.save_layout_alphbet);
					}).ContinueWith(delegate
					{
						OpenAnimation();
					});
				}
				else
				{
					_KeyboardControl?.Set_Lighting_Effect(4, _EffectData.save_effect, _EffectData.save_light, _EffectData.save_speed, _EffectData.save_direction, SAVED, _EffectData.save_layout_color, _EffectData.save_layout_backgroundcolor, _EffectData.save_layout_alphbet);
				}
				if (_EffectData.save_light == 0)
				{
					_KeyboardControl?.ILM_RGBKB_SetLightingPower(RGBKB_PowerStatus.Off);
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

	public virtual void CloseAnimation()
	{
		if (!_CloseAnimation || _PowerStatus != RGBKB_PowerStatus.On)
		{
			return;
		}
		try
		{
			if (_EffectData.save_effect != 51)
			{
				for (int num = _EffectData.save_light; num > 0; num -= 8)
				{
					SetBrightnessStrategy((byte)num, saveACDC: false);
					Thread.Sleep(num * 3);
				}
			}
			SetBrightnessStrategy(0, saveACDC: false);
		}
		catch
		{
		}
	}

	private void OpenAnimation()
	{
		if (!_OpenAnimation)
		{
			return;
		}
		_OpenAnimation = false;
		if (_EffectData.save_effect == 2 || _EffectData.save_effect == 10)
		{
			SetBrightnessStrategy(_EffectData.save_light);
		}
		else if (_EffectData.save_effect == 3 || _EffectData.save_effect == 14)
		{
			Thread.Sleep(100);
			for (int i = 0; i <= _EffectData.save_light; i += 8)
			{
				SetBrightnessStrategy((byte)i);
				Thread.Sleep(Convert.ToInt32((double)(50 - i) * 2.5));
			}
		}
		else
		{
			Thread.Sleep(50);
			for (int j = 0; j <= _EffectData.save_light; j += 8)
			{
				SetBrightnessStrategy((byte)j);
				Thread.Sleep((50 - j) * 2);
			}
		}
		_OpenAnimation = true;
	}

	internal void Dispose(bool disposing)
	{
		if (!disposed)
		{
			if (disposing)
			{
				this.m_Layout_Event_handler = null;
			}
			disposed = true;
		}
	}

	public void Dispose()
	{
		Dispose(disposing: true);
		GC.SuppressFinalize(this);
	}

	void IDisposable.Dispose()
	{
		//ILSpy generated this explicit interface implementation from .override directive in Dispose
		this.Dispose();
	}

	public virtual void Uninstall()
	{
	}

	public SAVE_LIGHTING_EFFECT_DATA GetAllKeyboardStatus()
	{
		return _EffectData;
	}

	public virtual bool GetSingleZonePowerSupport()
	{
		byte Data = 0;
		MyEcCtrl.Instance.Read("HIDKeyboard", 1934, ref Data);
		return new BitArray(new byte[1] { Data })[5];
	}

	public virtual int GetMonochromeIndex()
	{
		return 0;
	}

	public virtual int GetManualIndex1()
	{
		return 0;
	}

	public virtual int GetManualIndex2()
	{
		return 0;
	}

	public virtual int GetManualIndex3()
	{
		return 0;
	}

	public virtual int GetManualIndex4()
	{
		return 0;
	}

	public virtual int GetManualIndex5()
	{
		return 0;
	}

	public virtual int GetManualIndex6()
	{
		return 0;
	}

	public virtual int GetManualInterval()
	{
		return 0;
	}

	public virtual int GetBreathingIndex()
	{
		return 0;
	}

	public virtual string GetDefaultData()
	{
		return "";
	}

	public virtual RGBKB_Color GetLayoutColor()
	{
		return _EffectData.save_layout_color;
	}
}
