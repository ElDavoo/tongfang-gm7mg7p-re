using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using System.Timers;
using System.Windows;
using LightingModel;
using MyECIO;
using Utility;

namespace MyControlCenter.MyRgbKeyboard;

internal class SingleZone : HIDKeyboard
{
	private string className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	internal const string _SaveDefaultEffect = "DefaultEffect";

	internal const string _SaveDefaultRgbLevel = "DefaultRgbLevel";

	internal SAVE_EC_LIGHTING_EFFECT_DATA _DefaultEcEffectData;

	internal SAVE_EC_LIGHTING_EFFECT_DATA _EcEffectData;

	internal const int RGB_LEVEL_SCALES = 50;

	internal const int RGB_LEVEL_MIN = 1;

	internal const int RGB_LEVEL_MAX = 50;

	internal const int RGB_VALUE_TO_LEVEL_RATIO = 5;

	internal const int MONOCHROME_COLOR_INDEX_MIN = 1;

	internal const int MONOCHROME_COLOR_INDEX_MAX = 30;

	internal const int MANUAL_COLORS_COUNT = 6;

	internal static List<COLOR_CELL> m_color_cell = new List<COLOR_CELL>
	{
		new COLOR_CELL(1u, byte.MaxValue, 0, 0, 50, 0, 0),
		new COLOR_CELL(2u, byte.MaxValue, 50, 0, 50, 5, 0),
		new COLOR_CELL(3u, byte.MaxValue, 80, 0, 50, 10, 0),
		new COLOR_CELL(4u, 145, 60, 0, 29, 13, 0),
		new COLOR_CELL(5u, byte.MaxValue, 102, 0, 40, 10, 0),
		new COLOR_CELL(6u, byte.MaxValue, 128, 0, 40, 15, 0),
		new COLOR_CELL(7u, byte.MaxValue, 180, 0, 40, 25, 0),
		new COLOR_CELL(8u, 150, 128, 2, 35, 20, 0),
		new COLOR_CELL(9u, byte.MaxValue, 204, 0, 50, 40, 0),
		new COLOR_CELL(10u, 204, 225, 0, 40, 44, 0),
		new COLOR_CELL(11u, 120, byte.MaxValue, 0, 24, 50, 0),
		new COLOR_CELL(12u, 60, 115, 18, 12, 23, 4),
		new COLOR_CELL(13u, 0, byte.MaxValue, 0, 0, 50, 0),
		new COLOR_CELL(14u, 0, byte.MaxValue, 80, 0, 50, 16),
		new COLOR_CELL(15u, 0, byte.MaxValue, 180, 0, 50, 35),
		new COLOR_CELL(16u, 60, 125, 135, 13, 25, 26),
		new COLOR_CELL(17u, 0, byte.MaxValue, byte.MaxValue, 0, 50, 50),
		new COLOR_CELL(18u, 0, 180, byte.MaxValue, 0, 35, 50),
		new COLOR_CELL(19u, 0, 80, byte.MaxValue, 0, 16, 50),
		new COLOR_CELL(20u, 0, 35, 102, 0, 8, 20),
		new COLOR_CELL(21u, 0, 0, byte.MaxValue, 0, 0, 50),
		new COLOR_CELL(22u, 80, 0, byte.MaxValue, 16, 0, 50),
		new COLOR_CELL(23u, 180, 0, byte.MaxValue, 35, 0, 50),
		new COLOR_CELL(24u, 110, 45, 100, 21, 9, 19),
		new COLOR_CELL(25u, byte.MaxValue, 0, byte.MaxValue, 50, 0, 50),
		new COLOR_CELL(26u, byte.MaxValue, 0, 180, 50, 0, 36),
		new COLOR_CELL(27u, byte.MaxValue, 0, 80, 50, 0, 6),
		new COLOR_CELL(28u, 180, 5, 0, 36, 0, 0),
		new COLOR_CELL(29u, 0, 0, 0, 0, 0, 0),
		new COLOR_CELL(30u, byte.MaxValue, byte.MaxValue, byte.MaxValue, 50, 40, 40)
	};

	private COLOR_CELL EcDefaultRgb;

	private COLOR_CELL DefaultRgb;

	private COLOR_CELL SavedDefaultRgb;

	private static System.Timers.Timer _TimersTimer = new System.Timers.Timer();

	private object timer_init_lock = new object();

	private static bool timer_initialized = false;

	private static int m_Manual_colors_index = -1;

	private static int projectid;

	private static string project;

	private object _colorLock = new object();

	public SingleZone(LM_Manager lm_Manger, string fwVersion)
		: base(lm_Manger, fwVersion)
	{
		LogCtrl.TraceMessage(lm_Manger.m_KB_Type.ToString() + " Created.", ".ctor", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 135);
		try
		{
			projectid = _EcKeyboardControl.GetProjectID();
			project = projectid.ToString();
		}
		catch (Exception)
		{
		}
		InitManualMode();
		KeyboardCloseTimer.CreateInstance.ControlBrigtnessEvent -= CreateInstance_ControlBrigtnessEvent;
		KeyboardCloseTimer.CreateInstance.ControlBrigtnessEvent += CreateInstance_ControlBrigtnessEvent;
	}

	private void CreateInstance_ControlBrigtnessEvent(object sender, EventArgs e)
	{
		if (_PowerStatus == RGBKB_PowerStatus.On)
		{
			if (Convert.ToBoolean(sender))
			{
				StopManualMode();
				StopRainbowMode();
				StopBreathingMode();
				SetPowerDisable_EC(enable: true);
			}
			else
			{
				SetPowerDisable_EC(enable: false);
			}
		}
		else
		{
			StopManualMode();
			StopRainbowMode();
			StopBreathingMode();
			SetPowerDisable_EC(enable: true);
		}
	}

	internal byte Translate_EC_EffectIndex(RGBKB_Effect layoutEffect)
	{
		return layoutEffect switch
		{
			RGBKB_Effect.Single => 1, 
			RGBKB_Effect.Rainbow => 5, 
			RGBKB_Effect.Manual => 64, 
			RGBKB_Effect.Breathing => 2, 
			_ => byte.MaxValue, 
		};
	}

	public int RGBValueToLevel(int value, string colorName = "", int BaseRGB_Value = 5, int MinBsse = 1)
	{
		return (value / BaseRGB_Value).LimitToRange(MinBsse, 50);
	}

	internal void TranalteColorCellsRgbToLevel()
	{
		foreach (COLOR_CELL item in m_color_cell)
		{
			item.R_Level = Convert.ToByte(RGBValueToLevel(item.R, "R"));
			item.G_Level = Convert.ToByte(RGBValueToLevel(item.G, "G"));
			item.B_Level = Convert.ToByte(RGBValueToLevel(item.B, "B"));
			LogCtrl.Write(string.Format("new COLOR_CELL( {0}, {1}, {2}, {3}, {4}, {5}, {6}),  // 0x{7},0x{8},0x{9}", item.Index.ToString().PadLeft(2), item.R.ToString().PadLeft(3), item.G.ToString().PadLeft(3), item.B.ToString().PadLeft(3), item.R_Level.ToString().PadLeft(2), item.G_Level.ToString().PadLeft(2), item.B_Level.ToString().PadLeft(2), item.R_Level.ToString("X2").PadLeft(2, '0'), item.G_Level.ToString("X2").PadLeft(2, '0'), item.B_Level.ToString("X2").PadLeft(2, '0')));
		}
	}

	internal string GetEffectString(byte effect)
	{
		return effect switch
		{
			1 => "EFFECT_STATIC", 
			5 => "EFFECT_RAINBOW", 
			64 => "EFFECT_MANUAL", 
			2 => "EFFECT_BREATHING", 
			_ => "EFFECT_UNKNOWN", 
		};
	}

	public override async void InitalizeKeyboardEffect(bool unplug = false)
	{
		_ = 5;
		try
		{
			uint aclevel = await SettingsStorageExtensions.ReadAsync<uint>("", _SaveACLight);
			uint dclevel = await SettingsStorageExtensions.ReadAsync<uint>("", _SaveDCLight);
			RGBKB_PowerStatus powerstatus = await SettingsStorageExtensions.ReadAsync<RGBKB_PowerStatus>("", _SavePowerSwich);
			try
			{
				DefaultRgb = GetDefaultRGB();
				SavedDefaultRgb = await GetSavedDefaultRGB();
				_DefaultEcEffectData = await GetDefaultEffectData((int)DefaultRgb.Index);
				SAVE_EC_LIGHTING_EFFECT_DATA defaultEcEffectData = _DefaultEcEffectData;
				LogCtrl.TraceMessage("_DefaultEcEffectData : " + defaultEcEffectData.ToString(), "InitalizeKeyboardEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 278);
				if (DefaultRgb.R_Level != SavedDefaultRgb.R_Level || DefaultRgb.G_Level != SavedDefaultRgb.G_Level || DefaultRgb.B_Level != SavedDefaultRgb.B_Level)
				{
					SetSavedDefaultRGB(DefaultRgb);
					LogCtrl.TraceMessage("default RGB level changed, use default effect data", "InitalizeKeyboardEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 289);
					_EcEffectData = _DefaultEcEffectData;
				}
				else
				{
					LogCtrl.TraceMessage("default RGB level consistent, read saved effect data", "InitalizeKeyboardEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 296);
					SAVE_EC_LIGHTING_EFFECT_DATA ecEffectData = await SettingsStorageExtensions.ReadAsync<SAVE_EC_LIGHTING_EFFECT_DATA>(_EcKeyboardControl.ILM_RGBKB_GetRGBKeyboardType().ToString(), project + "_LastEffect");
					if (ecEffectData.save_effect == 0)
					{
						LogCtrl.TraceMessage("no saved effect data, use default one", "InitalizeKeyboardEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 302);
						_EcEffectData = _DefaultEcEffectData;
					}
					else
					{
						_EcEffectData = ecEffectData;
					}
				}
			}
			catch (Exception ex)
			{
				LogCtrl.TraceMessage("exception occured, use default effect data: " + ex, "InitalizeKeyboardEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 314);
				_EcEffectData = _DefaultEcEffectData;
			}
			_PowerStatus = powerstatus;
			SetPowerStatus(_PowerStatus);
			_AC_LightLevel = aclevel;
			_DC_LightLevel = dclevel;
			SetACDCLight(unplug, aclevel, dclevel);
		}
		catch (Exception)
		{
		}
		UpdatedBrightness();
	}

	internal override void SetACDCLight(bool unplug, uint aclevel, uint dclevel)
	{
		if (unplug)
		{
			CurrentPowerMode = RGBKB_PowerMode.DC;
			_DC_LightLevel = dclevel;
			SetBrightness_EC(dclevel);
		}
		else
		{
			CurrentPowerMode = RGBKB_PowerMode.AC;
			_AC_LightLevel = aclevel;
			SetBrightness_EC(aclevel);
		}
	}

	public override void AsyncWelcome()
	{
	}

	public override async void InitalizeWelcomeKeyboardEffect(RGBKB_PowerStatus power, bool IsAppExists, bool unplug = false)
	{
		_InitIsDone = true;
	}

	internal override void SaveEffectData()
	{
		SAVE_EC_LIGHTING_EFFECT_DATA ecEffectData = _EcEffectData;
		LogCtrl.TraceMessage("_EcEffectData = " + ecEffectData.ToString(), "SaveEffectData", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 402);
		try
		{
			string text = _EcKeyboardControl.GetProjectID().ToString();
			SettingsStorageExtensions.SaveAsync(_EcKeyboardControl.ILM_RGBKB_GetRGBKeyboardType().ToString(), text + "_LastEffect", _EcEffectData);
			if (CurrentPowerMode == RGBKB_PowerMode.AC)
			{
				SettingsStorageExtensions.SaveAsync("", _SaveACLight, _AC_LightLevel);
			}
			else if (CurrentPowerMode == RGBKB_PowerMode.DC)
			{
				SettingsStorageExtensions.SaveAsync("", _SaveDCLight, _DC_LightLevel);
			}
		}
		catch (Exception)
		{
		}
	}

	public override bool SetEffect(dynamic data)
	{
		RGBKB_Effect layoutEffect = data["effect"];
		SAVE_EC_LIGHTING_EFFECT_DATA sAVE_EC_LIGHTING_EFFECT_DATA = default(SAVE_EC_LIGHTING_EFFECT_DATA);
		SAVE_EC_LIGHTING_EFFECT_DATA sAVE_EC_LIGHTING_EFFECT_DATA2;
		try
		{
			sAVE_EC_LIGHTING_EFFECT_DATA.save_effect = Translate_EC_EffectIndex(layoutEffect);
			sAVE_EC_LIGHTING_EFFECT_DATA.MonochromeIndex = data["MonochromeIndex"];
			sAVE_EC_LIGHTING_EFFECT_DATA.ManualIndex1 = data["ManualIndex1"];
			sAVE_EC_LIGHTING_EFFECT_DATA.ManualIndex2 = data["ManualIndex2"];
			sAVE_EC_LIGHTING_EFFECT_DATA.ManualIndex3 = data["ManualIndex3"];
			sAVE_EC_LIGHTING_EFFECT_DATA.ManualIndex4 = data["ManualIndex4"];
			sAVE_EC_LIGHTING_EFFECT_DATA.ManualIndex5 = data["ManualIndex5"];
			sAVE_EC_LIGHTING_EFFECT_DATA.ManualIndex6 = data["ManualIndex6"];
			sAVE_EC_LIGHTING_EFFECT_DATA.ManualInterval = data["ManualInterval"];
			sAVE_EC_LIGHTING_EFFECT_DATA.BreathingIndex = data["BreathingIndex"];
			if (data["color"] != null)
			{
				sAVE_EC_LIGHTING_EFFECT_DATA.UserDefineColor = ConvertJsonRGB2RGBColor(data["color"]);
			}
			sAVE_EC_LIGHTING_EFFECT_DATA2 = sAVE_EC_LIGHTING_EFFECT_DATA;
			LogCtrl.TraceMessage("new effect : " + sAVE_EC_LIGHTING_EFFECT_DATA2.ToString(), "SetEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 454);
		}
		catch (Exception ex)
		{
			Exception ex2 = ex;
			Exception ex3 = ex2;
			Application.Current.Dispatcher?.BeginInvoke((Action)delegate
			{
				LogCtrl.TraceMessage("exception: " + ex3, "SetEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 464);
			});
			return false;
		}
		if (_EcEffectData.Equals(sAVE_EC_LIGHTING_EFFECT_DATA))
		{
			sAVE_EC_LIGHTING_EFFECT_DATA2 = _EcEffectData;
			LogCtrl.TraceMessage("effect same, _EcEffectData : " + sAVE_EC_LIGHTING_EFFECT_DATA2.ToString(), "SetEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 472);
			return false;
		}
		sAVE_EC_LIGHTING_EFFECT_DATA2 = _EcEffectData;
		LogCtrl.TraceMessage("new effect, _EcEffectData : " + sAVE_EC_LIGHTING_EFFECT_DATA2.ToString(), "SetEffect", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 477);
		_EcEffectData = sAVE_EC_LIGHTING_EFFECT_DATA;
		return true;
	}

	public override bool SetWelcomeEffect(dynamic data)
	{
		return false;
	}

	public override void SetPowerStatus(RGBKB_PowerStatus powerstatus)
	{
		if (!Monitor.TryEnter(_powerLock, 1500))
		{
			return;
		}
		try
		{
			_PowerStatus = powerstatus;
			if (powerstatus == RGBKB_PowerStatus.Off)
			{
				StopManualMode();
				StopRainbowMode();
				StopBreathingMode();
				SetPowerDisable_EC(enable: true);
				SavePowerStatus();
			}
			else
			{
				SetPowerDisable_EC(enable: false);
				if (_EcEffectData.save_effect != 0)
				{
					RunEffct(0);
				}
				SavePowerStatus();
			}
		}
		finally
		{
			Monitor.Exit(_powerLock);
		}
	}

	private void SetPowerDisable_EC(bool enable)
	{
		byte Data = 0;
		MyEcCtrl.Instance.Read("HIDKeyboard", 1932, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		bitArray[1] = enable;
		byte data = ConvertToByte(bitArray);
		MyEcCtrl.Instance.Write("HIDKeyboard", 1932, data);
	}

	private void SetBrightness_EC(uint level)
	{
		byte Data = 0;
		MyEcCtrl.Instance.Read("HIDKeyboard", 1932, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		switch (level)
		{
		case 1u:
			bitArray[4] = true;
			bitArray[5] = true;
			bitArray[6] = false;
			bitArray[7] = false;
			break;
		case 2u:
			bitArray[4] = true;
			bitArray[5] = false;
			bitArray[6] = true;
			bitArray[7] = false;
			break;
		case 3u:
			bitArray[4] = true;
			bitArray[5] = true;
			bitArray[6] = true;
			bitArray[7] = false;
			break;
		case 4u:
			bitArray[4] = true;
			bitArray[5] = false;
			bitArray[6] = false;
			bitArray[7] = true;
			break;
		default:
			bitArray[4] = true;
			bitArray[5] = false;
			bitArray[6] = false;
			bitArray[7] = false;
			break;
		}
		byte data = ConvertToByte(bitArray);
		MyEcCtrl.Instance.Write("HIDKeyboard", 1932, data);
		SaveEffectData();
	}

	public override void SetBrinessByScanCode(int scancode)
	{
		LogCtrl.Write("SingleZone Scancode : " + scancode);
		switch (scancode)
		{
		case 59:
			if (_PowerStatus == RGBKB_PowerStatus.Off)
			{
				SetPowerStatus(RGBKB_PowerStatus.On);
			}
			SetBrightness(0u);
			UpdatedBrightness();
			break;
		case 60:
			if (_PowerStatus == RGBKB_PowerStatus.Off)
			{
				SetPowerStatus(RGBKB_PowerStatus.On);
			}
			SetBrightness(1u);
			UpdatedBrightness();
			break;
		case 61:
			if (_PowerStatus == RGBKB_PowerStatus.Off)
			{
				SetPowerStatus(RGBKB_PowerStatus.On);
			}
			SetBrightness(2u);
			UpdatedBrightness();
			break;
		case 62:
			if (_PowerStatus == RGBKB_PowerStatus.Off)
			{
				SetPowerStatus(RGBKB_PowerStatus.On);
			}
			SetBrightness(3u);
			UpdatedBrightness();
			break;
		case 63:
			if (_PowerStatus == RGBKB_PowerStatus.Off)
			{
				SetPowerStatus(RGBKB_PowerStatus.On);
			}
			SetBrightness(4u);
			UpdatedBrightness();
			break;
		}
	}

	private uint ConvertToLevel(BitArray bit)
	{
		if (bit[7])
		{
			return 4u;
		}
		if (bit[5] && bit[6])
		{
			return 3u;
		}
		if (bit[6])
		{
			return 2u;
		}
		if (bit[5])
		{
			return 1u;
		}
		return 0u;
	}

	private void UpdatedBrightness()
	{
		RGBKB_Event_Data event_data = new RGBKB_Event_Data
		{
			event_id = RGBKB_EventID.Brightness_update,
			envet_data_len = 2u,
			event_data = new byte[1]
		};
		event_data.event_data[0] = Convert.ToByte(GetBrightness());
		ScanCodeUpdatedBrightness(event_data);
	}

	public override void UnPlugged()
	{
		CurrentPowerMode = RGBKB_PowerMode.DC;
		SetBrightness_EC(_DC_LightLevel);
		UpdatedBrightness();
	}

	public override void Plugged()
	{
		CurrentPowerMode = RGBKB_PowerMode.AC;
		SetBrightness_EC(_AC_LightLevel);
		UpdatedBrightness();
	}

	internal override void PluggedSetBrightness(uint brightness)
	{
	}

	public override void SetBrightness(uint level)
	{
		if (CurrentPowerMode == RGBKB_PowerMode.DC)
		{
			_DC_LightLevel = level;
		}
		else
		{
			_AC_LightLevel = level;
		}
		SetBrightness_EC(level);
	}

	public override uint GetBrightness()
	{
		if (CurrentPowerMode == RGBKB_PowerMode.DC)
		{
			return _DC_LightLevel;
		}
		return _AC_LightLevel;
	}

	public override void SetBrightness_ACDC(uint ACBrightness, uint DCBrighteness, bool saveACDC = true)
	{
	}

	internal override void SetBrightnessStrategy(byte brightness, bool saveACDC = true)
	{
		LogCtrl.TraceMessage("brightness = " + brightness + ", saveACDC = " + saveACDC + "   do nothing , return", "SetBrightnessStrategy", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 772);
	}

	public override void RunWelcomeEffect()
	{
	}

	public override void RunEffct(byte SAVED = 0)
	{
		LogCtrl.TraceMessage("---BEGIN---", "RunEffct", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 783);
		LogCtrl.Indent();
		if (_PowerStatus == RGBKB_PowerStatus.On)
		{
			SetColorMode(_EcEffectData);
			SaveEffectData();
		}
		LogCtrl.Unindent();
		LogCtrl.TraceMessage("---END---", "RunEffct", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 793);
	}

	public override void CloseAnimation()
	{
	}

	public override void Uninstall()
	{
		LogCtrl.TraceMessage("", "Uninstall", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 808);
		try
		{
			SetRGBLevel(EcDefaultRgb.R_Level, EcDefaultRgb.G_Level, EcDefaultRgb.B_Level);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage(ex.ToString(), "Uninstall", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 816);
		}
	}

	public override int GetMonochromeIndex()
	{
		LogCtrl.TraceMessage(_EcEffectData.MonochromeIndex.ToString(), "GetMonochromeIndex", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 824);
		return _EcEffectData.MonochromeIndex;
	}

	public override int GetManualIndex1()
	{
		LogCtrl.TraceMessage(_EcEffectData.ManualIndex1.ToString(), "GetManualIndex1", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 830);
		return _EcEffectData.ManualIndex1;
	}

	public override int GetManualIndex2()
	{
		LogCtrl.TraceMessage(_EcEffectData.ManualIndex2.ToString(), "GetManualIndex2", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 836);
		return _EcEffectData.ManualIndex2;
	}

	public override int GetManualIndex3()
	{
		LogCtrl.TraceMessage(_EcEffectData.ManualIndex3.ToString(), "GetManualIndex3", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 842);
		return _EcEffectData.ManualIndex3;
	}

	public override int GetManualIndex4()
	{
		LogCtrl.TraceMessage(_EcEffectData.ManualIndex4.ToString(), "GetManualIndex4", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 848);
		return _EcEffectData.ManualIndex4;
	}

	public override int GetManualIndex5()
	{
		LogCtrl.TraceMessage(_EcEffectData.ManualIndex5.ToString(), "GetManualIndex5", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 854);
		return _EcEffectData.ManualIndex5;
	}

	public override int GetManualIndex6()
	{
		LogCtrl.TraceMessage(_EcEffectData.ManualIndex6.ToString(), "GetManualIndex6", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 860);
		return _EcEffectData.ManualIndex6;
	}

	public override int GetManualInterval()
	{
		LogCtrl.TraceMessage(_EcEffectData.ManualInterval.ToString(), "GetManualInterval", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 866);
		return _EcEffectData.ManualInterval;
	}

	public override int GetBreathingIndex()
	{
		LogCtrl.TraceMessage(_EcEffectData.BreathingIndex.ToString(), "GetBreathingIndex", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 872);
		return _EcEffectData.BreathingIndex;
	}

	public override string GetDefaultData()
	{
		LogCtrl.TraceMessage(_DefaultEcEffectData.ToString(), "GetDefaultData", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 878);
		return _DefaultEcEffectData.ToString();
	}

	private async Task<SAVE_EC_LIGHTING_EFFECT_DATA> GetDefaultEffectData(int _monoIndex)
	{
		SAVE_EC_LIGHTING_EFFECT_DATA result;
		try
		{
			result = await SettingsStorageExtensions.ReadAsync<SAVE_EC_LIGHTING_EFFECT_DATA>(_EcKeyboardControl.ILM_RGBKB_GetRGBKeyboardType().ToString(), project + "_DefaultEffect");
			if (result.save_effect == 0)
			{
				throw new Exception("No predefined default effect data for project 0x" + projectid.ToString("X2"));
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage(ex.ToString(), "GetDefaultEffectData", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 901);
			result = new SAVE_EC_LIGHTING_EFFECT_DATA
			{
				save_effect = Translate_EC_EffectIndex(RGBKB_Effect.Single),
				MonochromeIndex = 1,
				ManualIndex1 = 1,
				ManualIndex2 = 5,
				ManualIndex3 = 9,
				ManualIndex4 = 13,
				ManualIndex5 = 21,
				ManualIndex6 = 25,
				ManualInterval = 10,
				BreathingIndex = 1
			};
		}
		if (_monoIndex >= 1 && _monoIndex <= 30)
		{
			LogCtrl.TraceMessage("default monochrom index " + _monoIndex, "GetDefaultEffectData", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 919);
			result.MonochromeIndex = _monoIndex;
		}
		return result;
	}

	private COLOR_CELL GetDefaultRGB()
	{
		COLOR_CELL cOLOR_CELL = new COLOR_CELL(0u, 0, 0, 0, 0, 0, 0);
		try
		{
			EcDefaultRgb = GetEcDefaultRGB();
			cOLOR_CELL = ((EcDefaultRgb.Index != 0) ? EcDefaultRgb : m_color_cell.Find((COLOR_CELL x) => x.Index == 1));
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage(ex.ToString(), "GetDefaultRGB", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 952);
		}
		LogCtrl.TraceMessage($"default RGB : {cOLOR_CELL}", "GetDefaultRGB", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 954);
		return cOLOR_CELL;
	}

	private COLOR_CELL GetEcDefaultRGB()
	{
		ulong num = 0uL;
		COLOR_CELL _EcDefaultRgb = new COLOR_CELL(0u, 0, 0, 0, 0, 0, 0);
		try
		{
			num = 0uL;
			ReadECRAM(1900, ref num);
			_EcDefaultRgb.R_Level = Convert.ToByte(num);
			num = 0uL;
			ReadECRAM(1901, ref num);
			_EcDefaultRgb.G_Level = Convert.ToByte(num);
			num = 0uL;
			ReadECRAM(1902, ref num);
			_EcDefaultRgb.B_Level = Convert.ToByte(num);
			COLOR_CELL cOLOR_CELL = m_color_cell.Find((COLOR_CELL cell) => cell.R_Level == _EcDefaultRgb.R_Level && cell.G_Level == _EcDefaultRgb.G_Level && cell.B_Level == _EcDefaultRgb.B_Level);
			if (cOLOR_CELL != null)
			{
				_EcDefaultRgb = cOLOR_CELL;
			}
			else
			{
				LogCtrl.TraceMessage("Error: EC default RGB level not matching any predefined color", "GetEcDefaultRGB", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 985);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage(ex.ToString(), "GetEcDefaultRGB", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 990);
		}
		LogCtrl.TraceMessage($"EC default RGB : {_EcDefaultRgb}", "GetEcDefaultRGB", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 992);
		return _EcDefaultRgb;
	}

	private async Task<COLOR_CELL> GetSavedDefaultRGB()
	{
		COLOR_CELL _EcDefaultRgbSaved = new COLOR_CELL(0u, 0, 0, 0, 0, 0, 0);
		try
		{
			SAVE_DEFUALT_RGB_LEVEL sAVE_DEFUALT_RGB_LEVEL = await SettingsStorageExtensions.ReadAsync<SAVE_DEFUALT_RGB_LEVEL>(_EcKeyboardControl.ILM_RGBKB_GetRGBKeyboardType().ToString() + "\\Default", project + "_DefaultRgbLevel");
			_EcDefaultRgbSaved.R_Level = sAVE_DEFUALT_RGB_LEVEL.R_Level;
			_EcDefaultRgbSaved.G_Level = sAVE_DEFUALT_RGB_LEVEL.G_Level;
			_EcDefaultRgbSaved.B_Level = sAVE_DEFUALT_RGB_LEVEL.B_Level;
			LogCtrl.TraceMessage($"get saved default RGB : {sAVE_DEFUALT_RGB_LEVEL}", "GetSavedDefaultRGB", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1011);
		}
		catch
		{
			LogCtrl.TraceMessage("No saved default RGB level found", "GetSavedDefaultRGB", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1015);
		}
		return _EcDefaultRgbSaved;
	}

	private void SetSavedDefaultRGB(COLOR_CELL _cell)
	{
		SAVE_DEFUALT_RGB_LEVEL sAVE_DEFUALT_RGB_LEVEL = default(SAVE_DEFUALT_RGB_LEVEL);
		sAVE_DEFUALT_RGB_LEVEL.R_Level = _cell.R_Level;
		sAVE_DEFUALT_RGB_LEVEL.G_Level = _cell.G_Level;
		sAVE_DEFUALT_RGB_LEVEL.B_Level = _cell.B_Level;
		LogCtrl.TraceMessage($"set saved default RGB : {sAVE_DEFUALT_RGB_LEVEL}", "SetSavedDefaultRGB", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1029);
		SettingsStorageExtensions.SaveAsync(_EcKeyboardControl.ILM_RGBKB_GetRGBKeyboardType().ToString() + "\\Default", project + "_DefaultRgbLevel", sAVE_DEFUALT_RGB_LEVEL);
	}

	public void SetRGBColor(int R, int G, int B)
	{
		int num = RGBValueToLevel(R, "R");
		int num2 = RGBValueToLevel(G, "G", 6);
		int num3 = RGBValueToLevel(B, "B", 6);
		foreach (COLOR_CELL item in m_color_cell.Take(m_color_cell.Count - 1))
		{
			if (item.R == R && item.G == G && item.B == B)
			{
				num2 = RGBValueToLevel(G, "G");
				num3 = RGBValueToLevel(B, "B");
			}
		}
		if (R == 255 && G == 255 && B == 255)
		{
			num = 50;
			num2 = 40;
			num3 = 40;
		}
		else if (R == 255 && G == 0 && B == 80)
		{
			num = 50;
			num2 = 0;
			num3 = 6;
		}
		else if (R == 255 && G == 50 && B == 0)
		{
			num = 50;
			num2 = 5;
			num3 = 0;
		}
		else if (R == 255 && G == 80 && B == 0)
		{
			num = 50;
			num2 = 10;
			num3 = 0;
		}
		else if (R == 145 && G == 60 && B == 0)
		{
			num = 45;
			num2 = 13;
			num3 = 0;
		}
		else if (R == 255 && G == 102 && B == 0)
		{
			num = 40;
			num2 = 10;
			num3 = 0;
		}
		else if (R == 255 && G == 128 && B == 0)
		{
			num = 40;
			num2 = 15;
			num3 = 0;
		}
		else if (R == 255 && G == 180 && B == 0)
		{
			num = 40;
			num2 = 25;
			num3 = 0;
		}
		else if (R == 150 && G == 128 && B == 2)
		{
			num = 35;
			num2 = 20;
			num3 = 0;
		}
		LogCtrl.TraceMessage($"RGB: ({R}, {G}, {B}), level: ({num}, {num2}, {num3})", "SetRGBColor", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1133);
		SetRGBLevel(num, num2, num3);
	}

	public void SetRGBLevel(int level_r, int level_g, int level_b)
	{
		WriteECRAM(1897, (ulong)level_r, "SetRGBLevel");
		WriteECRAM(1898, (ulong)level_g, "SetRGBLevel");
		WriteECRAM(1899, (ulong)level_b, "SetRGBLevel");
		ulong Value = 0uL;
		ReadECRAM(1895, ref Value);
		BitArray bitArray = new BitArray(new byte[1] { Convert.ToByte(Value) });
		bitArray[5] = true;
		byte b = ConvertToByte(bitArray);
		WriteECRAM(1895, b, "SetRGBLevel");
	}

	public void StopRainbowMode()
	{
		ulong Value = 0uL;
		ReadECRAM(1895, ref Value);
		BitArray bitArray = new BitArray(new byte[1] { Convert.ToByte(Value) });
		bitArray[7] = false;
		byte b = ConvertToByte(bitArray);
		WriteECRAM(1895, b, "StopRainbowMode");
	}

	public void StartRainbowMode()
	{
		WriteECRAM(1897, 0uL, "StartRainbowMode");
		WriteECRAM(1898, 0uL, "StartRainbowMode");
		WriteECRAM(1899, 0uL, "StartRainbowMode");
		ulong Value = 0uL;
		ReadECRAM(1895, ref Value);
		BitArray bitArray = new BitArray(new byte[1] { Convert.ToByte(Value) });
		bitArray[7] = true;
		byte b = ConvertToByte(bitArray);
		WriteECRAM(1895, b, "StartRainbowMode");
	}

	private void InitManualMode()
	{
		if (!Monitor.TryEnter(timer_init_lock, 100))
		{
			return;
		}
		try
		{
			if (!timer_initialized)
			{
				_TimersTimer.Interval = double.MaxValue;
				_TimersTimer.AutoReset = true;
				_TimersTimer.Elapsed -= _TimersTimer_Elapsed;
				_TimersTimer.Elapsed += _TimersTimer_Elapsed;
				m_Manual_colors_index = -1;
				timer_initialized = true;
			}
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("exception: " + ex, "InitManualMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1210);
		}
		finally
		{
			Monitor.Exit(timer_init_lock);
		}
	}

	public void StartManualMode()
	{
		try
		{
			_TimersTimer.Interval = _EcEffectData.ManualInterval * 1000;
			_TimersTimer.Stop();
			_TimersTimer.Start();
			_TimersTimer_Elapsed(_TimersTimer, null);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("exception: " + ex, "StartManualMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1230);
		}
	}

	public void StopManualMode()
	{
		try
		{
			_TimersTimer.Stop();
			m_Manual_colors_index = -1;
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("exception: " + ex, "StopManualMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1243);
		}
	}

	private void _TimersTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		ManualMix();
	}

	private void ManualBreath()
	{
		try
		{
			int num = ((m_Manual_colors_index < 1 || m_Manual_colors_index >= 6) ? 1 : (m_Manual_colors_index + 1));
			int next_color_idx = GetManualColorIndex(num);
			COLOR_CELL cOLOR_CELL = m_color_cell.Find((COLOR_CELL x) => x.Index == next_color_idx);
			int num2 = num - 1;
			if (num2 == 0)
			{
				num2 = 6;
			}
			int before_color_idx = GetManualColorIndex(num2);
			COLOR_CELL cOLOR_CELL2 = m_color_cell.Find((COLOR_CELL x) => x.Index == before_color_idx);
			byte b = 0;
			byte b2 = 0;
			byte b3 = 0;
			int num3 = 5;
			int num4 = 200;
			if (_TimersTimer.Interval == 2000.0)
			{
				num3 = 4;
				num4 = Convert.ToInt32(_TimersTimer.Interval / (double)num3 * 0.25);
			}
			else
			{
				num4 = Convert.ToInt32(_TimersTimer.Interval / (double)num3 * 0.33);
			}
			if (cOLOR_CELL2 == null)
			{
				RGB_S[] colorBuffer = _EcEffectData.UserDefineColor.ColorBuffer;
				new COLOR_CELL(51u, colorBuffer[num2].R, colorBuffer[num2].G, colorBuffer[num2].B, 0, 0, 0);
			}
			if (cOLOR_CELL != null)
			{
				for (int num5 = 0; num5 <= num3; num5++)
				{
					if (_TimersTimer.Enabled)
					{
						b = Convert.ToByte(cOLOR_CELL.R * num5 / num3);
						b2 = Convert.ToByte(cOLOR_CELL.G * num5 / num3);
						b3 = Convert.ToByte(cOLOR_CELL.B * num5 / num3);
						SetRGBColor(b, b2, b3);
						Thread.Sleep(num4);
						continue;
					}
					return;
				}
				Thread.Sleep(num4 * 2);
				for (int num6 = 0; num6 <= num3; num6++)
				{
					if (!_TimersTimer.Enabled)
					{
						break;
					}
					b = Convert.ToByte(cOLOR_CELL.R * (num3 - num6) / num3);
					b2 = Convert.ToByte(cOLOR_CELL.G * (num3 - num6) / num3);
					b3 = Convert.ToByte(cOLOR_CELL.B * (num3 - num6) / num3);
					SetRGBColor(b, b2, b3);
					Thread.Sleep(num4);
				}
				return;
			}
			RGB_S[] colorBuffer2 = _EcEffectData.UserDefineColor.ColorBuffer;
			for (int num7 = 0; num7 <= num3; num7++)
			{
				if (_TimersTimer.Enabled)
				{
					b = Convert.ToByte(colorBuffer2[num].R * num7 / num3);
					b2 = Convert.ToByte(colorBuffer2[num].G * num7 / num3);
					b3 = Convert.ToByte(colorBuffer2[num].B * num7 / num3);
					SetRGBColor(b, b2, b3);
					Thread.Sleep(num4);
					continue;
				}
				return;
			}
			Thread.Sleep(num4 * 2);
			for (int num8 = 0; num8 <= num3; num8++)
			{
				if (_TimersTimer.Enabled)
				{
					b = Convert.ToByte(colorBuffer2[num].R * (num3 - num8) / num3);
					b2 = Convert.ToByte(colorBuffer2[num].G * (num3 - num8) / num3);
					b3 = Convert.ToByte(colorBuffer2[num].B * (num3 - num8) / num3);
					SetRGBColor(b, b2, b3);
					Thread.Sleep(num4);
					continue;
				}
				return;
			}
			LogCtrl.TraceMessage("Error: can not find color with id  and run custom clor id " + next_color_idx, "ManualBreath", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1385);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("exception: " + ex, "ManualBreath", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1391);
		}
	}

	private void ManualMix()
	{
		try
		{
			int num = ((m_Manual_colors_index < 1 || m_Manual_colors_index >= 6) ? 1 : (m_Manual_colors_index + 1));
			int next_color_idx = GetManualColorIndex(num);
			LogCtrl.TraceMessage("prev index = " + m_Manual_colors_index + ", next_index = " + num + ", next_color_idx = " + next_color_idx, "ManualMix", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1415);
			COLOR_CELL cOLOR_CELL = m_color_cell.Find((COLOR_CELL x) => x.Index == next_color_idx);
			int num2 = num - 1;
			if (num2 == 0)
			{
				num2 = 6;
			}
			int before_color_idx = GetManualColorIndex(num2);
			COLOR_CELL cOLOR_CELL2 = m_color_cell.Find((COLOR_CELL x) => x.Index == before_color_idx);
			byte b = 0;
			byte b2 = 0;
			byte b3 = 0;
			int num3 = 5;
			int num4 = 200;
			if (_TimersTimer.Interval == 2000.0)
			{
				num3 = 4;
				num4 = Convert.ToInt32(_TimersTimer.Interval / (double)num3 * 0.5);
			}
			else
			{
				num4 = Convert.ToInt32(_TimersTimer.Interval / (double)num3 * 0.66);
			}
			if (cOLOR_CELL2 == null)
			{
				RGB_S[] colorBuffer = _EcEffectData.UserDefineColor.ColorBuffer;
				cOLOR_CELL2 = new COLOR_CELL(51u, colorBuffer[num2].R, colorBuffer[num2].G, colorBuffer[num2].B, 0, 0, 0);
			}
			if (cOLOR_CELL != null)
			{
				for (int num5 = 1; num5 <= num3; num5++)
				{
					if (_TimersTimer.Enabled)
					{
						b = Convert.ToByte(cOLOR_CELL2.R * (num3 - num5) / num3 + cOLOR_CELL.R * num5 / num3);
						b2 = Convert.ToByte(cOLOR_CELL2.G * (num3 - num5) / num3 + cOLOR_CELL.G * num5 / num3);
						b3 = Convert.ToByte(cOLOR_CELL2.B * (num3 - num5) / num3 + cOLOR_CELL.B * num5 / num3);
						SetRGBColor(b, b2, b3);
						Thread.Sleep(num4);
						continue;
					}
					return;
				}
			}
			else
			{
				RGB_S[] colorBuffer2 = _EcEffectData.UserDefineColor.ColorBuffer;
				for (int num6 = 1; num6 <= num3; num6++)
				{
					if (_TimersTimer.Enabled)
					{
						b = Convert.ToByte(cOLOR_CELL2.R * (num3 - num6) / num3 + colorBuffer2[num].R * num6 / num3);
						b2 = Convert.ToByte(cOLOR_CELL2.G * (num3 - num6) / num3 + colorBuffer2[num].G * num6 / num3);
						b3 = Convert.ToByte(cOLOR_CELL2.B * (num3 - num6) / num3 + colorBuffer2[num].B * num6 / num3);
						SetRGBColor(b, b2, b3);
						Thread.Sleep(num4);
						continue;
					}
					return;
				}
				LogCtrl.TraceMessage("Error: can not find color with id  and run custom clor id " + next_color_idx, "ManualMix", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1496);
			}
			m_Manual_colors_index = num;
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("exception: " + ex, "ManualMix", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1503);
		}
	}

	private int GetManualColorIndex(int idx)
	{
		int result = 1;
		switch (idx)
		{
		case 1:
			result = _EcEffectData.ManualIndex1;
			break;
		case 2:
			result = _EcEffectData.ManualIndex2;
			break;
		case 3:
			result = _EcEffectData.ManualIndex3;
			break;
		case 4:
			result = _EcEffectData.ManualIndex4;
			break;
		case 5:
			result = _EcEffectData.ManualIndex5;
			break;
		case 6:
			result = _EcEffectData.ManualIndex6;
			break;
		default:
			LogCtrl.TraceMessage("Error: unhandled index " + idx, "GetManualColorIndex", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1533);
			break;
		}
		return result;
	}

	private void StopBreathingMode()
	{
		StartBreathingMode(0);
	}

	private void StartBreathingMode(int BreathingColorIndex)
	{
		ulong Value = 0uL;
		ReadECRAM(1989, ref Value);
		Value &= 0xF8;
		switch (BreathingColorIndex)
		{
		case 1:
			Value++;
			break;
		case 2:
			Value += 2;
			break;
		case 3:
			Value += 3;
			break;
		case 4:
			Value += 4;
			break;
		}
		WriteECRAM(1989, Value, "StartBreathingMode");
	}

	public void SetColorMode(SAVE_EC_LIGHTING_EFFECT_DATA _effect_data)
	{
		LogCtrl.TraceMessage("_effect = 0x" + _effect_data.save_effect.ToString("X2") + " " + GetEffectString(_effect_data.save_effect), "SetColorMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1584);
		COLOR_CELL cOLOR_CELL;
		switch (_effect_data.save_effect)
		{
		case 1:
		{
			StopRainbowMode();
			StopManualMode();
			StopBreathingMode();
			cOLOR_CELL = m_color_cell.Find((COLOR_CELL x) => x.Index == _effect_data.MonochromeIndex);
			if (cOLOR_CELL != null)
			{
				SetRGBColor(cOLOR_CELL.R, cOLOR_CELL.G, cOLOR_CELL.B);
				return;
			}
			RGB_S[] colorBuffer = _EcEffectData.UserDefineColor.ColorBuffer;
			SetRGBColor(colorBuffer[0].R, colorBuffer[0].G, colorBuffer[0].B);
			return;
		}
		case 5:
			StopManualMode();
			StopBreathingMode();
			StartRainbowMode();
			return;
		case 64:
			StopRainbowMode();
			StopManualMode();
			StopBreathingMode();
			StartManualMode();
			return;
		case 2:
			StopRainbowMode();
			StopManualMode();
			StartBreathingMode(_effect_data.BreathingIndex);
			return;
		}
		LogCtrl.TraceMessage("Warn: unknow effect " + _effect_data.save_effect, "SetColorMode", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1627);
		StopRainbowMode();
		StopManualMode();
		StopBreathingMode();
		cOLOR_CELL = m_color_cell.Find((COLOR_CELL x) => x.Index == _effect_data.MonochromeIndex);
		if (cOLOR_CELL != null)
		{
			SetRGBColor(cOLOR_CELL.R, cOLOR_CELL.G, cOLOR_CELL.B);
			return;
		}
		RGB_S[] colorBuffer2 = _EcEffectData.UserDefineColor.ColorBuffer;
		SetRGBColor(colorBuffer2[0].R, colorBuffer2[0].G, colorBuffer2[0].B);
	}

	private void ReadECRAM(ushort Addr, ref ulong Value)
	{
		try
		{
			byte Data = 0;
			MyEcCtrl.Instance.Read(className, Addr, ref Data);
			Value = (byte)Convert.ToUInt64(Data);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage(ex.ToString(), "ReadECRAM", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MyRgbKeyboard\\HIDKeyboard\\SingleZone.cs", 1658);
		}
	}

	private void WriteECRAM(ushort Addr, ulong Value, [CallerMemberName] string memberName = "")
	{
		EcCtrl.Write(className, Addr, Convert.ToByte(Value));
	}
}
