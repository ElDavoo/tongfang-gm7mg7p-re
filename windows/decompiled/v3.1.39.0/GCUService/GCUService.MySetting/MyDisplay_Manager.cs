using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows;
using System.Windows.Threading;
using MyControlCenter;
using Utility;

namespace GCUService.MySetting;

internal class MyDisplay_Manager
{
	private static readonly MyDisplay_Manager control = new MyDisplay_Manager();

	private const string DisplayStatus = "Display/Status";

	private MyMagSetFullscreenColorEffect vibrant;

	private ColorSpaceEffect colorSpace;

	private const string DisplaySaveName = "DisplayTableSetting";

	private bool _DisplaySwitch;

	private string _CurrentSelectedName = "VibrantMode";

	private List<ColorControl> profileNameList = new List<ColorControl>();

	private SettingsManager _SettingsManager;

	private MySettingManager _MySetting;

	private object setEffectlock = new object();

	public static MyDisplay_Manager Instance => control;

	private MyDisplay_Manager()
	{
		if (RegistryCtrl.GetCustomizeTarget() != 11)
		{
			_SettingsManager = new SettingsManager(string.Concat(Directory.GetParent(Assembly.GetExecutingAssembly().Location)?.ToString() + "\\DisplayProfile\\", "DisplayTable.json"));
			vibrant = new MyMagSetFullscreenColorEffect();
			colorSpace = new ColorSpaceEffect();
			InitEffect();
		}
	}

	public void InitEffect()
	{
		Application.Current.Dispatcher.BeginInvoke((Action)delegate
		{
			InitalizeColorProfile();
		}, DispatcherPriority.Background);
	}

	private async void InitalizeColorProfile()
	{
		try
		{
			profileNameList.Clear();
			try
			{
				_SettingsManager.GetSetting<DisplaySave>("DisplayTableSetting", out var result);
				if (result != null)
				{
					_DisplaySwitch = result.DisplaySwitch;
					_CurrentSelectedName = result.CurrentSelectName;
					profileNameList = result.ProfileNameList;
					LoadProfile();
					Console.WriteLine("Load display json successful ! " + _CurrentSelectedName);
					LogCtrl.Write("Load display json successful !" + DateTime.Now.ToString());
				}
			}
			catch
			{
				LogCtrl.Write("Load display json error !");
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Load display json error !" + ex.ToString());
		}
	}

	private void LoadProfile()
	{
		try
		{
			if (_DisplaySwitch)
			{
				ColorControl colorControl = profileNameList.SingleOrDefault((ColorControl n) => n.colorProfileName.Equals(_CurrentSelectedName));
				if (colorControl != null)
				{
					SetCustomEffect(colorControl);
				}
				else
				{
					SetDefaultForWindows();
				}
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Load display json error !" + ex.ToString());
		}
	}

	public void SetSettingMnager(MySettingManager mysetting)
	{
		_MySetting = mysetting;
	}

	internal async void Receive(byte[] message)
	{
		string msgString = Encoding.UTF8.GetString(message);
		dynamic val = await Json.ToObjectAsync<object>(msgString);
		if (val["Action"] != null)
		{
			if (val["Action"] == "GETSTATUS")
			{
				GetDisplayStatus();
			}
			else if (val["Action"] == "Default")
			{
				ColorControl colorCmd = new ColorControl();
				string profile = val["Profile"];
				colorCmd.colorProfileName = profile;
				colorCmd.brightness = 55;
				colorCmd.ColorTemp = 6500;
				colorCmd.Gamma = 1f;
				colorCmd.VibrantValue = 1f;
				colorCmd.Constrast = 1f;
				colorCmd.ColorR = 128.0;
				colorCmd.ColorG = 128.0;
				colorCmd.ColorB = 128.0;
				colorSpace.SetBrightness(colorCmd.brightness);
				colorSpace.SetColorTemp(colorCmd.ColorTemp);
				colorSpace.SetGamma(colorCmd.Gamma);
				Application.Current.Dispatcher.BeginInvoke((Action)delegate
				{
					switch (profile)
					{
					case "VibrantMode":
						colorCmd.brightness = 50;
						colorSpace.SetBrightness(colorCmd.brightness);
						colorSpace.VibrantMode();
						colorSpace.ExecuteSettings();
						colorCmd.VibrantValue = 1.5f;
						vibrant.SaturationMartrixSetting(colorCmd.VibrantValue);
						break;
					case "VideoMode":
						colorSpace.VideoMode();
						colorSpace.ExecuteSettings();
						vibrant.ContrastMartrixSetting(colorCmd.Constrast);
						break;
					case "InternetMode":
						colorSpace.InternetMode();
						colorSpace.ExecuteSettings();
						vibrant.ContrastMartrixSetting(colorCmd.Constrast);
						break;
					case "LowBlueMode":
						colorCmd.brightness = 50;
						colorSpace.SetBrightness(colorCmd.brightness);
						colorCmd.ColorTemp = 5000;
						colorSpace.SetColorTemp(colorCmd.ColorTemp);
						colorSpace.LowBlueMode();
						colorSpace.ExecuteSettings();
						vibrant.ContrastMartrixSetting(colorCmd.Constrast);
						break;
					case "CinemaMode":
						colorCmd.ColorTemp = 6000;
						colorSpace.SetColorTemp(colorCmd.ColorTemp);
						colorSpace.CinemaMode();
						colorSpace.ExecuteSettings();
						vibrant.ContrastMartrixSetting(colorCmd.Constrast);
						break;
					case "PhotoMode":
						colorSpace.PhotoMode();
						colorSpace.ExecuteSettings();
						vibrant.ContrastMartrixSetting(colorCmd.Constrast);
						break;
					default:
						vibrant.SaturationMartrixSetting();
						vibrant.ContrastMartrixSetting();
						break;
					case "GrayLevelMode":
						break;
					}
					double[] colorRGB = colorSpace.GetColorRGB();
					colorCmd.ColorR = colorRGB[0];
					colorCmd.ColorG = colorRGB[1];
					colorCmd.ColorB = colorRGB[2];
					CheckProfile(profile, colorCmd);
					SaveCommand(asyncToUi: true);
				}, DispatcherPriority.Background);
			}
			else
			{
				if (!((val["Action"] == "EffectSwitch") ? true : false))
				{
					return;
				}
				try
				{
					if ((bool)val["Switch"])
					{
						_DisplaySwitch = true;
					}
					else
					{
						_DisplaySwitch = false;
					}
					if (_DisplaySwitch && profileNameList.Count > 0)
					{
						ColorControl colorControl = profileNameList?.SingleOrDefault((ColorControl a) => a.colorProfileName.Equals(_CurrentSelectedName));
						if (colorControl != null)
						{
							SetCustomEffect(colorControl);
						}
						else
						{
							SetCustomEffect(profileNameList[0]);
						}
					}
					else
					{
						SetDefaultForWindows();
						_MySetting?.ColoCalibrationService();
					}
				}
				catch (Exception ex)
				{
					LogCtrl.Write("[MyDisplay] : " + ex.ToString());
				}
			}
		}
		else
		{
			ColorControl customEffect = await Json.ToObjectAsync<ColorControl>(msgString);
			if (_DisplaySwitch)
			{
				SetCustomEffect(customEffect);
			}
			else
			{
				SetDefaultForWindows();
			}
		}
	}

	public void SetDisplaySwitch(bool ONOFF)
	{
		_DisplaySwitch = ONOFF;
		SaveCommand(asyncToUi: true);
	}

	public void GetDisplayStatus()
	{
		DisplaySave displaySave = new DisplaySave();
		displaySave.DisplaySwitch = _DisplaySwitch;
		displaySave.CurrentSelectName = _CurrentSelectedName;
		displaySave.ProfileNameList = profileNameList;
		App.m_MQTTService.Publish("Display/Status", displaySave, retain: false);
	}

	private void SetDefaultForWindows()
	{
		Application.Current.Dispatcher.BeginInvoke((Action)delegate
		{
			colorSpace?.Default();
			colorSpace?.ExecuteSettings();
			vibrant?.ContrastMartrixSetting();
			SaveCommand(asyncToUi: true);
		}, DispatcherPriority.Background);
	}

	private void SetCustomEffect(ColorControl colorCmd)
	{
		if (colorCmd.colorProfileName == null)
		{
			return;
		}
		string profile = colorCmd.colorProfileName;
		Application.Current.Dispatcher.BeginInvoke((Action)delegate
		{
			if (Monitor.TryEnter(setEffectlock, 200))
			{
				try
				{
					colorSpace.SetBrightness(colorCmd.brightness);
					colorSpace.SetColorTemp(colorCmd.ColorTemp);
					colorSpace.SetGamma(colorCmd.Gamma);
					switch (profile)
					{
					case "VibrantMode":
						colorSpace.VibrantMode();
						colorSpace.SetColor(colorCmd.ColorR, colorCmd.ColorG, colorCmd.ColorB);
						colorSpace.ExecuteSettings();
						vibrant.SaturationMartrixSetting(colorCmd.VibrantValue);
						break;
					case "VideoMode":
						colorSpace.VideoMode();
						colorSpace.SetColor(colorCmd.ColorR, colorCmd.ColorG, colorCmd.ColorB);
						colorSpace.ExecuteSettings();
						vibrant.ContrastMartrixSetting(colorCmd.Constrast);
						break;
					case "InternetMode":
						colorSpace.InternetMode();
						colorSpace.SetColor(colorCmd.ColorR, colorCmd.ColorG, colorCmd.ColorB);
						colorSpace.ExecuteSettings();
						vibrant.ContrastMartrixSetting(colorCmd.Constrast);
						break;
					case "LowBlueMode":
						colorSpace.LowBlueMode();
						colorSpace.SetColor(colorCmd.ColorR, colorCmd.ColorG, colorCmd.ColorB);
						colorSpace.ExecuteSettings();
						vibrant.ContrastMartrixSetting(colorCmd.Constrast);
						break;
					case "CinemaMode":
						colorSpace.CinemaMode();
						colorSpace.SetColor(colorCmd.ColorR, colorCmd.ColorG, colorCmd.ColorB);
						colorSpace.ExecuteSettings();
						vibrant.ContrastMartrixSetting(colorCmd.Constrast);
						break;
					case "PhotoMode":
						colorSpace.PhotoMode();
						colorSpace.SetColor(colorCmd.ColorR, colorCmd.ColorG, colorCmd.ColorB);
						colorSpace.ExecuteSettings();
						vibrant.ContrastMartrixSetting(colorCmd.Constrast);
						break;
					default:
						colorSpace.SetColor(255.0, 255.0, 255.0);
						colorSpace.ExecuteSettings();
						vibrant.SaturationMartrixSetting();
						vibrant.ContrastMartrixSetting();
						break;
					case "GrayLevelMode":
						break;
					}
					_CurrentSelectedName = profile;
					CheckProfile(profile, colorCmd);
					SaveCommand();
				}
				catch (Exception)
				{
				}
				finally
				{
					Monitor.Exit(setEffectlock);
				}
			}
		}, DispatcherPriority.Background);
	}

	private void SaveCommand(bool asyncToUi = false)
	{
		DisplaySave displaySave = new DisplaySave();
		displaySave.DisplaySwitch = _DisplaySwitch;
		displaySave.CurrentSelectName = _CurrentSelectedName;
		displaySave.ProfileNameList = profileNameList;
		_SettingsManager.AddSetting("DisplayTableSetting", displaySave);
		_SettingsManager.SaveSettings();
		if (asyncToUi)
		{
			App.m_MQTTService.Publish("Display/Status", displaySave, retain: false);
		}
	}

	private void CheckProfile(string profile, ColorControl colorCmd)
	{
		int num = profileNameList.FindIndex((ColorControl n) => n.colorProfileName.Equals(profile));
		if (num != -1)
		{
			profileNameList[num] = colorCmd;
		}
		else
		{
			profileNameList.Add(colorCmd);
		}
	}
}
