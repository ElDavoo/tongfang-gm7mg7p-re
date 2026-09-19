using System;
using System.CodeDom.Compiler;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Forms;
using System.Windows.Markup;
using Microsoft.Win32;
using RegistryUtils;
using Utility;

namespace MyControlCenter;

public class TrayView : Window, IComponentConnector
{
	private static MyFanCtrl m_MyFan = MyFanCtrl.Instance;

	private NotifyIcon notifyIcon = new NotifyIcon
	{
		ContextMenuStrip = new ContextMenuStrip(),
		Visible = true
	};

	private static RegistryMonitor registryMonitor;

	private string m_sAppName = "Gaming Center U";

	public static string m_sAPPTarget = "STD";

	public static int m_nAppType = 1;

	public static string m_sAppIcon = "gamingcenter256.ico";

	public static int m_nCustomizeTarget = 1;

	public static string m_sTitleName = "NA";

	public static int m_nTitleNameType = 1;

	private string m_sLang = "en-us";

	private string m_sRegPath = "\\OEM\\GamingCenter2";

	public static string m_sTrayIconFile = "TrayIcon";

	private string m_GCU_EXE = "GamingCenterU.exe";

	private string m_sGCU = "GamingCenterU";

	private ResourceDictionary m_dict_new = new ResourceDictionary();

	private System.Windows.Forms.ContextMenu cm1 = new System.Windows.Forms.ContextMenu();

	private System.Windows.Forms.MenuItem item;

	private uint m_count;

	private int m_ProjectID;

	private System.Windows.Forms.MenuItem item_GamingMode = new System.Windows.Forms.MenuItem();

	private System.Windows.Forms.MenuItem item_OfficeMode = new System.Windows.Forms.MenuItem();

	private System.Windows.Forms.MenuItem item_TurboMode = new System.Windows.Forms.MenuItem();

	private object TrayIconDrawingLock = new object();

	internal Grid rootGrid;

	private bool _contentLoaded;

	public NotifyIcon GetNotifyIcon()
	{
		return notifyIcon;
	}

	public TrayView(uint _count, int _ProjectID)
	{
		LogCtrl.Write("Tray Start");
		GetCustomizeTarget();
		if (RegistryCtrl.GetBridgeType() == 1)
		{
			return;
		}
		ReflashTray.RefreshTrayArea();
		InitializeComponent();
		SetResourceDictionary();
		GetEXEName();
		UpdateParams(_count, _ProjectID);
		if (App.OsdOnly != 1)
		{
			item = new System.Windows.Forms.MenuItem();
			item.Name = "ItemLaunch";
			if (m_sAPPTarget.Equals("STD"))
			{
				item.Click += notifyIcon_DoubleClick;
				item.Text = FindResource("strTrayLaunch").ToString();
				cm1.MenuItems.Add(item);
			}
			else if (m_sAPPTarget.Equals("Customize"))
			{
				if (m_nTitleNameType == 1)
				{
					item.Text = FindResource("strTrayLaunch").ToString();
				}
				else if (m_nTitleNameType == 2)
				{
					switch (m_sLang)
					{
					case "en-us":
						item.Text = "Enable " + m_sAppName;
						break;
					case "zh-cn":
						item.Text = "打开 " + m_sAppName;
						break;
					case "tr-tr":
						item.Text = m_sAppName + "'ni Aç";
						break;
					case "zh-tw":
						item.Text = "打開 " + m_sAppName;
						break;
					case "de-de":
						item.Text = m_sAppName + " Starten";
						break;
					case "ko-kr":
						item.Text = m_sAppName + " 활성화";
						break;
					case "ru-ru":
						item.Text = "Включить " + m_sAppName;
						break;
					case "ja-jp":
						item.Text = "表示";
						break;
					case "pl-pl":
						item.Text = "Włącz " + m_sAppName;
						break;
					case "es-es":
						item.Text = "Habilitar " + m_sAppName;
						break;
					case "fr-fr":
						item.Text = "Activer le " + m_sAppName;
						break;
					case "pt-br":
						item.Text = "Ativar " + m_sAppName;
						break;
					case "hu-hu":
						item.Text = m_sAppName + " Engedélyezése";
						break;
					}
				}
				item.Click += notifyIcon_DoubleClick;
				cm1.MenuItems.Add(item);
			}
			else
			{
				item.Click += notifyIcon_DoubleClick;
				item.Text = FindResource("strTrayLaunch").ToString();
				cm1.MenuItems.Add(item);
			}
		}
		item = new System.Windows.Forms.MenuItem();
		item.Name = "ItemFanMode";
		if (m_ProjectID >= 11)
		{
			item.Text = FindResource("strTrayOperatingModes").ToString();
		}
		else
		{
			item.Text = FindResource("strTrayModeSwitch").ToString();
		}
		cm1.MenuItems.Add(item);
		item_GamingMode = new System.Windows.Forms.MenuItem();
		item_GamingMode.Click += item_GamingMode_Click;
		if (!m_ProjectID.IsProjectId_Commercial())
		{
			item_GamingMode.Text = FindResource("strTrayGamingMode").ToString();
		}
		else
		{
			item_GamingMode.Text = FindResource("strTrayBalanceMode").ToString();
		}
		item.MenuItems.Add(item_GamingMode);
		item_OfficeMode = new System.Windows.Forms.MenuItem();
		item_OfficeMode.Click += item_OfficeMode_Click;
		if (!m_ProjectID.IsProjectId_Commercial())
		{
			item_OfficeMode.Text = FindResource("strTrayOfficeMode").ToString();
		}
		else
		{
			item_OfficeMode.Text = FindResource("strTray20dbMode").ToString();
		}
		item.MenuItems.Add(item_OfficeMode);
		if (m_count == 3)
		{
			item_TurboMode = new System.Windows.Forms.MenuItem();
			item_TurboMode.Click += item_TurboMode_Click;
			item_TurboMode.Text = FindResource("strTrayTurboMode").ToString();
			item.MenuItems.Add(item_TurboMode);
		}
		item = new System.Windows.Forms.MenuItem();
		item.Name = "ItemExit";
		item.Click += item_ExitClick;
		item.Text = FindResource("strTrayExit").ToString();
		cm1.MenuItems.Add(item);
		DrawIcon();
		UpdateItemStatus();
		notifyIcon.ContextMenu = cm1;
		notifyIcon.Text = m_sAppName;
		notifyIcon.Click += notifyIcon_Click;
		notifyIcon.DoubleClick += notifyIcon_DoubleClick;
		base.Closing += MainWindow_Closing;
		notifyIcon.BalloonTipClosed += delegate(object sender, EventArgs e)
		{
			NotifyIcon obj = (NotifyIcon)sender;
			obj.Visible = false;
			obj.Dispose();
		};
		SystemEvents.DisplaySettingsChanged += SystemEvents_DisplaySettingsChanged;
		registryMonitor = new RegistryMonitor("HKEY_LOCAL_MACHINE\\SOFTWARE\\OEM\\GamingCenter2");
		registryMonitor.RegChanged += OnRegChanged2;
		registryMonitor.Start();
		LogCtrl.Write("Tray End");
	}

	private void UpdateParams(uint _count, int _ProjectID)
	{
		m_count = _count;
		m_ProjectID = _ProjectID;
	}

	private void SystemEvents_DisplaySettingsChanged(object sender, EventArgs e)
	{
		LogCtrl.Write("SystemEvents_DisplaySettingsChanged");
		DrawIcon();
		UpdateItemStatus();
		Thread.Sleep(1000);
	}

	private void item_GamingMode_Click(object sender, EventArgs e)
	{
		m_MyFan.m_Manager.UserSet_Mode1();
		if (App.OsdOnly == 1)
		{
			App.m_Osd.ShowOSDByName(m_MyFan.m_Manager.g_FanMode);
		}
		m_MyFan.m_Manager.UpdateStatusToClient(1);
	}

	private void item_OfficeMode_Click(object sender, EventArgs e)
	{
		m_MyFan.m_Manager.UserSet_Mode2();
		if (App.OsdOnly == 1)
		{
			App.m_Osd.ShowOSDByName(m_MyFan.m_Manager.g_FanMode);
		}
		m_MyFan.m_Manager.UpdateStatusToClient(1);
	}

	private void item_TurboMode_Click(object sender, EventArgs e)
	{
		m_MyFan.m_Manager.UserSet_Mode3();
		if (App.OsdOnly == 1)
		{
			App.m_Osd.ShowOSDByName(m_MyFan.m_Manager.g_FanMode);
		}
		m_MyFan.m_Manager.UpdateStatusToClient(1);
	}

	private void item_ExitClick(object sender, EventArgs e)
	{
		LogCtrl.Write("item_ExitClick");
		try
		{
			Process[] processesByName = Process.GetProcessesByName(m_sGCU);
			for (int i = 0; i < processesByName.Count(); i++)
			{
				string action = "System_OFF";
				App.m_MQTTService.Publish("System/Control", new
				{
					Action = action
				}, retain: false);
				Thread.Sleep(500);
				processesByName[i].Kill();
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("[item_ExitClick] Kill " + ex.ToString());
		}
		Thread.Sleep(500);
		registryMonitor.RegChanged -= OnRegChanged2;
		Close();
	}

	private void notifyIcon_Click(object sender, EventArgs e)
	{
		LogCtrl.Write("notifyIcon_Click");
		if (App.OsdOnly != 1)
		{
			return;
		}
		try
		{
			if ((e as MouseEventArgs).Button == MouseButtons.Left)
			{
				typeof(NotifyIcon).GetMethod("ShowContextMenu", BindingFlags.Instance | BindingFlags.NonPublic).Invoke((NotifyIcon)sender, null);
			}
		}
		catch
		{
		}
	}

	private void notifyIcon_DoubleClick(object sender, EventArgs e)
	{
		LogCtrl.Write("notifyIcon_DoubleClick");
		if (App.OsdOnly != 1)
		{
			LaunchAP();
		}
	}

	public void LaunchAP()
	{
		try
		{
			string text = LogCtrl.GetParentDirectoryPath(new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName, 2) + "\\GamingCenter";
			LogCtrl.Write($"BaseDirectoryPath = {text}");
			if (text != "")
			{
				CreateProcessAsUserWrapper.LaunchChildProcess(text + "\\" + m_GCU_EXE);
			}
			else
			{
				LogCtrl.Write("AP not found.");
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("LaunchAP Exception: " + ex.Message);
		}
	}

	private void MainWindow_Closing(object sender, CancelEventArgs e)
	{
		LogCtrl.Write("TrayMainWindow_Closing");
		registryMonitor.RegChanged -= OnRegChanged2;
		notifyIcon.Visible = false;
		notifyIcon.Dispose();
		notifyIcon = null;
	}

	private void OnRegChanged2(object sender, EventArgs e)
	{
		string text = "en-us";
		try
		{
			text = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "Language", "en-us");
		}
		catch
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath, "Language", m_sLang, RegistryValueKind.String);
		}
		if (text != m_sLang)
		{
			LanguageChanged();
		}
	}

	private void LanguageChanged()
	{
		cm1.Dispose();
		item.Dispose();
		cm1 = new System.Windows.Forms.ContextMenu();
		item_GamingMode.Dispose();
		item_OfficeMode.Dispose();
		item_GamingMode = new System.Windows.Forms.MenuItem();
		item_OfficeMode = new System.Windows.Forms.MenuItem();
		if (m_count == 3)
		{
			item_TurboMode.Dispose();
			item_TurboMode = new System.Windows.Forms.MenuItem();
		}
		SetResourceDictionary();
		if (App.OsdOnly != 1)
		{
			item = new System.Windows.Forms.MenuItem();
			item.Name = "ItemLaunch";
			if (m_sAPPTarget.Equals("STD"))
			{
				item.Click += notifyIcon_DoubleClick;
				item.Text = FindResource("strTrayLaunch").ToString();
				cm1.MenuItems.Add(item);
			}
			else if (m_sAPPTarget.Equals("Customize"))
			{
				if (m_nTitleNameType == 1)
				{
					item.Text = FindResource("strTrayLaunch").ToString();
				}
				else if (m_nTitleNameType == 2)
				{
					switch (m_sLang)
					{
					case "en-us":
						item.Text = "Enable " + m_sAppName;
						break;
					case "zh-cn":
						item.Text = "打开 " + m_sAppName;
						break;
					case "tr-tr":
						item.Text = m_sAppName + "'ni Aç";
						break;
					case "zh-tw":
						item.Text = "打開 " + m_sAppName;
						break;
					case "de-de":
						item.Text = m_sAppName + " Starten";
						break;
					case "ko-kr":
						item.Text = m_sAppName + " 활성화";
						break;
					case "ru-ru":
						item.Text = "Включить " + m_sAppName;
						break;
					case "ja-jp":
						item.Text = "表示";
						break;
					case "pl-pl":
						item.Text = "Włącz " + m_sAppName;
						break;
					case "es-es":
						item.Text = "Habilitar " + m_sAppName;
						break;
					case "fr-fr":
						item.Text = "Activer le " + m_sAppName;
						break;
					case "pt-br":
						item.Text = "Ativar " + m_sAppName;
						break;
					case "hu-hu":
						item.Text = m_sAppName + " Engedélyezése";
						break;
					}
				}
				item.Click += notifyIcon_DoubleClick;
				cm1.MenuItems.Add(item);
			}
			else
			{
				item.Click += notifyIcon_DoubleClick;
				item.Text = FindResource("strTrayLaunch").ToString();
				cm1.MenuItems.Add(item);
			}
		}
		try
		{
			item = new System.Windows.Forms.MenuItem();
			item.Name = "ItemFanMode";
			if (m_ProjectID >= 11)
			{
				item.Text = FindResource("strTrayOperatingModes")?.ToString();
			}
			else
			{
				item.Text = FindResource("strTrayModeSwitch")?.ToString();
			}
			cm1.MenuItems.Add(item);
			item_GamingMode = new System.Windows.Forms.MenuItem();
			item_GamingMode.Click += item_GamingMode_Click;
			if (!m_ProjectID.IsProjectId_Commercial())
			{
				item_GamingMode.Text = FindResource("strTrayGamingMode")?.ToString();
			}
			else
			{
				item_GamingMode.Text = FindResource("strTrayBalanceMode")?.ToString();
			}
			item.MenuItems.Add(item_GamingMode);
			item_OfficeMode = new System.Windows.Forms.MenuItem();
			item_OfficeMode.Click += item_OfficeMode_Click;
			if (!m_ProjectID.IsProjectId_Commercial())
			{
				item_OfficeMode.Text = FindResource("strTrayOfficeMode")?.ToString();
			}
			else
			{
				item_OfficeMode.Text = FindResource("strTray20dbMode")?.ToString();
			}
			item.MenuItems.Add(item_OfficeMode);
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Fan Mode Switch error:" + ex.ToString());
		}
		if (m_count == 3)
		{
			item_TurboMode = new System.Windows.Forms.MenuItem();
			item_TurboMode.Click += item_TurboMode_Click;
			item_TurboMode.Text = FindResource("strTrayTurboMode")?.ToString();
			item.MenuItems.Add(item_TurboMode);
		}
		item = new System.Windows.Forms.MenuItem();
		item.Name = "ItemExit";
		item.Click += item_ExitClick;
		item.Text = FindResource("strTrayExit")?.ToString();
		cm1.MenuItems.Add(item);
		if (notifyIcon != null)
		{
			notifyIcon.ContextMenu = cm1;
			UpdateItemStatus();
		}
	}

	private void SetResourceDictionary()
	{
		try
		{
			m_sLang = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "Language", "en-us");
		}
		catch
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath, "Language", m_sLang, RegistryValueKind.String);
		}
		ResourceDictionary dict = new ResourceDictionary();
		switch (m_sLang)
		{
		case "en-us":
			dict.Source = new Uri("..\\Tray\\Language\\en-US.xaml", UriKind.Relative);
			break;
		case "zh-cn":
			dict.Source = new Uri("..\\Tray\\Language\\zh-CN.xaml", UriKind.Relative);
			break;
		case "tr-tr":
			dict.Source = new Uri("..\\Tray\\Language\\tr-Tr.xaml", UriKind.Relative);
			break;
		case "zh-tw":
			dict.Source = new Uri("..\\Tray\\Language\\zh-TW.xaml", UriKind.Relative);
			break;
		case "de-de":
			dict.Source = new Uri("..\\Tray\\Language\\de-DE.xaml", UriKind.Relative);
			break;
		case "hu-hu":
			dict.Source = new Uri("..\\Tray\\Language\\hu-HU.xaml", UriKind.Relative);
			break;
		case "ko-kr":
			dict.Source = new Uri("..\\Tray\\Language\\ko-KR.xaml", UriKind.Relative);
			break;
		case "ru-ru":
			dict.Source = new Uri("..\\Tray\\Language\\ru-RU.xaml", UriKind.Relative);
			break;
		case "ja-jp":
			dict.Source = new Uri("..\\Tray\\Language\\ja-JP.xaml", UriKind.Relative);
			break;
		case "pl-pl":
			dict.Source = new Uri("..\\Tray\\Language\\pl-PL.xaml", UriKind.Relative);
			break;
		case "es-es":
			dict.Source = new Uri("..\\Tray\\Language\\es-ES.xaml", UriKind.Relative);
			break;
		case "fr-fr":
			dict.Source = new Uri("..\\Tray\\Language\\fr-FR.xaml", UriKind.Relative);
			break;
		case "pt-br":
			dict.Source = new Uri("..\\Tray\\Language\\pt-BR.xaml", UriKind.Relative);
			break;
		default:
			dict.Source = new Uri("..\\Tray\\Language\\en-US.xaml", UriKind.Relative);
			break;
		}
		try
		{
			base.Dispatcher.Invoke(delegate
			{
				base.Resources.MergedDictionaries.Add(dict);
			});
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"TrayView | SetResourceDictionary | MergedDictionaries Failed {ex.ToString()}");
		}
		try
		{
			base.Dispatcher.Invoke(delegate
			{
				ReflashUIString<object>();
			});
		}
		catch (Exception ex2)
		{
			LogCtrl.Write($"TrayView | SetResourceDictionary | ReflashUIString Failed {ex2.ToString()}");
		}
	}

	private void GetCustomizeTarget()
	{
		try
		{
			m_sAppName = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "AppName", "Gaming Center U");
			m_sAPPTarget = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "APPTarget", "STD");
			m_nAppType = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "AppType", 1);
			m_sAppIcon = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "AppIcon", "gamingcenter256.ico");
			m_nCustomizeTarget = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "CustomizeTarget", 1);
			m_sTitleName = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "TitleName", "NA");
			m_nTitleNameType = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "TitleNameType", 1);
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"TrayView | GetCustomizeTarget | RegistrySoftwareKeyRead Failed {ex.ToString()}");
		}
	}

	private void GetEXEName()
	{
		switch (m_nAppType)
		{
		case 1:
			m_sGCU = "GamingCenterU";
			break;
		case 2:
			m_sGCU = "ControlCenterU";
			break;
		case 3:
			m_sGCU = "CreatorCenter";
			break;
		}
		if (m_nCustomizeTarget == 9)
		{
			m_sGCU = "ControlCenterU";
		}
		m_GCU_EXE = m_sGCU + ".exe";
		LogCtrl.TraceMessage("m_GCU_EXE: " + m_GCU_EXE, "GetEXEName", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Tray\\TrayView.xaml.cs", 702);
	}

	public void DrawIcon()
	{
		if (!Monitor.TryEnter(TrayIconDrawingLock, 500))
		{
			return;
		}
		try
		{
			string text = string.Concat(LogCtrl.GetParentDirectoryPath(System.Windows.Forms.Application.StartupPath, 2) + "\\logo", "\\", m_sTrayIconFile, "\\");
			if (TrayCtrl.m_icon_name != string.Empty)
			{
				m_sAppIcon = TrayCtrl.m_icon_name;
			}
			if (!File.Exists(text + m_sAppIcon))
			{
				Stream stream = System.Windows.Application.GetResourceStream(new Uri("pack://application:,,,/Tray/TrayIcon/" + m_sAppIcon)).Stream;
				if (stream != null)
				{
					notifyIcon.Icon = new Icon(stream);
				}
			}
			else if (File.Exists(text + m_sAppIcon) && notifyIcon != null)
			{
				notifyIcon.Icon = new Icon(text + m_sAppIcon);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"TrayView | DrawIcon | Drawing Failed {ex.ToString()}");
		}
		finally
		{
			Monitor.Exit(TrayIconDrawingLock);
		}
	}

	public string GetAppIconName()
	{
		return m_sAppIcon;
	}

	public void UpdateItemStatus()
	{
		try
		{
			switch (TrayCtrl.m_item_mode)
			{
			case 0u:
				item_GamingMode.Checked = true;
				item_OfficeMode.Checked = false;
				if (m_count == 3)
				{
					item_TurboMode.Checked = false;
				}
				break;
			case 1u:
				item_GamingMode.Checked = false;
				item_OfficeMode.Checked = true;
				if (m_count == 3)
				{
					item_TurboMode.Checked = false;
				}
				break;
			case 2u:
				item_GamingMode.Checked = false;
				item_OfficeMode.Checked = false;
				if (m_count == 3)
				{
					item_TurboMode.Checked = true;
				}
				break;
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"TrayView | UpdateItemStatus Failed {ex.ToString()}");
		}
	}

	private async Task<T> ReflashUIString<T>()
	{
		string sLang = m_sLang;
		List<string> LanganguageKey = new List<string>
		{
			"strTrayLaunch", "strTrayModeSwitch", "strTrayOperatingModes", "strTrayGamingMode", "strTrayOfficeMode", "strTrayBalanceMode", "strTray20dbMode", "strTrayBasicMode", "strTraySilentMode", "strTrayTurboMode",
			"strTrayExit"
		};
		dynamic fileResource = null;
		try
		{
			fileResource = await LoadLanguageResourceFromPath<object>(sLang, Assembly.GetExecutingAssembly());
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"TrayView | ReflashUIString | LoadLanguageResourceFromPath Failed {ex.ToString()}");
		}
		if (fileResource != null)
		{
			m_dict_new.Clear();
			try
			{
				foreach (string item in LanganguageKey)
				{
					string value = ((fileResource.ContainsKey(item)) ? fileResource[item] : null);
					m_dict_new.Add(item, value);
				}
			}
			catch (Exception ex2)
			{
				LogCtrl.Write($"TrayView | ReflashUIString | fileResource.ContainsKey Failed {ex2.ToString()}");
			}
			try
			{
				base.Dispatcher.Invoke(delegate
				{
					base.Resources.MergedDictionaries.Add(m_dict_new);
					foreach (System.Windows.Forms.MenuItem menuItem in cm1.MenuItems)
					{
						switch (menuItem.Name)
						{
						case "ItemLaunch":
							menuItem.Text = FindResource("strTrayLaunch")?.ToString();
							break;
						case "ItemFanMode":
							if (m_ProjectID >= 11)
							{
								menuItem.Text = FindResource("strTrayOperatingModes")?.ToString();
							}
							else
							{
								menuItem.Text = FindResource("strTrayModeSwitch")?.ToString();
							}
							break;
						case "ItemExit":
							menuItem.Text = FindResource("strTrayExit")?.ToString();
							break;
						default:
							LogCtrl.TraceMessage("Warning: menuitem without name, text=" + menuItem.Text, "ReflashUIString", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\Tray\\TrayView.xaml.cs", 845);
							break;
						}
					}
					if (!m_ProjectID.IsProjectId_Commercial())
					{
						item_GamingMode.Text = FindResource("strTrayGamingMode")?.ToString();
						item_OfficeMode.Text = FindResource("strTrayOfficeMode")?.ToString();
					}
					else
					{
						item_GamingMode.Text = FindResource("strTrayBalanceMode")?.ToString();
						item_OfficeMode.Text = FindResource("strTray20dbMode")?.ToString();
					}
					if (m_count == 3)
					{
						item_TurboMode.Text = FindResource("strTrayTurboMode")?.ToString();
					}
				});
			}
			catch (Exception ex3)
			{
				LogCtrl.Write($"TrayView | ReflashUIString | MergedDictionaries Failed {ex3.ToString()}");
			}
		}
		return default(T);
	}

	private static async Task<T> LoadLanguageResourceFromPath<T>(string language, Assembly assembly)
	{
		string path = string.Concat(LogCtrl.GetParentDirectoryPath(System.Windows.Forms.Application.StartupPath, 2) + "\\logo", "\\Language\\", language, ".json");
		if (File.Exists(path))
		{
			return await Json.ToObjectAsync<T>(File.ReadAllText(path));
		}
		return default(T);
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
	public void InitializeComponent()
	{
		if (!_contentLoaded)
		{
			_contentLoaded = true;
			Uri resourceLocator = new Uri("/GCUService;component/tray/trayview.xaml", UriKind.Relative);
			System.Windows.Application.LoadComponent(this, resourceLocator);
		}
	}

	void IComponentConnector.InitializeComponent()
	{
		//ILSpy generated this explicit interface implementation from .override directive in InitializeComponent
		this.InitializeComponent();
	}

	[DebuggerNonUserCode]
	[GeneratedCode("PresentationBuildTasks", "4.0.0.0")]
	[EditorBrowsable(EditorBrowsableState.Never)]
	void IComponentConnector.Connect(int connectionId, object target)
	{
		if (connectionId == 1)
		{
			rootGrid = (Grid)target;
		}
		else
		{
			_contentLoaded = true;
		}
	}
}
