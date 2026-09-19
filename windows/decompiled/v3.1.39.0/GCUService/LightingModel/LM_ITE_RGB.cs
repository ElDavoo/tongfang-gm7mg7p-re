using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Media;
using AudioLib;
using GCUService.MySystem;
using Microsoft.Win32.SafeHandles;
using MyControlCenter;
using MyControlCenter.MyRgbKeyboard;
using MyECIO;
using OemServiceModel;
using UsbHidModel;
using Utility;

namespace LightingModel;

internal class LM_ITE_RGB : ITE_SPEC, ILM_RGBKB
{
	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

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

	private BatteryPercentManger battry = new BatteryPercentManger();

	private byte NightMode;

	private int NightModeSelectColorIndex;

	private AudioData audioData;

	public int ColShift;

	public int ColRightShift;

	private bool _SingleTimeChangeFlag;

	private byte _asyncSingleBrightness = 50;

	private List<RGBKB_Type> MEZone_2p1ndSeries = new List<RGBKB_Type>
	{
		RGBKB_Type.MEZone_2p1nd_85,
		RGBKB_Type.MEZone_2p1nd_86,
		RGBKB_Type.MEZone_2p1nd_87,
		RGBKB_Type.MEZone_2p1nd_88
	};

	private List<RGBKB_Type> MEZone_2p2ndSeries = new List<RGBKB_Type>
	{
		RGBKB_Type.MEZone_2p2nd_97,
		RGBKB_Type.MEZone_2p2nd_98,
		RGBKB_Type.MEZone_2p2nd_99,
		RGBKB_Type.MEZone_2p2nd_100
	};

	private List<RGBKB_Type> MEZone_LightbarSeries = new List<RGBKB_Type>
	{
		RGBKB_Type.MEZone_Lighbar,
		RGBKB_Type.MEZone_Lighbar2
	};

	private bool BatteryEnable;

	private List<System.Windows.Media.Color> DefalutColorList = new List<System.Windows.Media.Color>
	{
		System.Windows.Media.Color.FromArgb(byte.MaxValue, byte.MaxValue, 0, 0),
		System.Windows.Media.Color.FromArgb(byte.MaxValue, byte.MaxValue, 165, 0),
		System.Windows.Media.Color.FromArgb(byte.MaxValue, byte.MaxValue, byte.MaxValue, 0),
		System.Windows.Media.Color.FromArgb(byte.MaxValue, 0, byte.MaxValue, 0),
		System.Windows.Media.Color.FromArgb(byte.MaxValue, 0, 0, byte.MaxValue),
		System.Windows.Media.Color.FromArgb(byte.MaxValue, 0, 127, byte.MaxValue),
		System.Windows.Media.Color.FromArgb(byte.MaxValue, 139, 0, byte.MaxValue)
	};

	private bool BeforeLevelIsDisable;

	private object _08HLock = new object();

	private Stopwatch sw1 = new Stopwatch();

	private Dictionary<RGBKB_Type, AudioData> audioDevices = new Dictionary<RGBKB_Type, AudioData>();

	private List<List<RGB_S>> VerticalColorList;

	private Stopwatch sw = new Stopwatch();

	private int AnimationShift = 7;

	private int shiftCount;

	private int shiftvalue = 1;

	private float EqualsMachMax;

	private float EqualsMachMin = float.MaxValue;

	private object lock_12h_test = new object();

	private object usbTransferLock = new object();

	public byte UserModeLight;

	private List<byte[]> perKBBuffer = new List<byte[]>
	{
		new byte[0],
		new byte[0],
		new byte[0],
		new byte[0],
		new byte[0],
		new byte[0]
	};

	private List<byte[]> perLBBuffer = new List<byte[]>
	{
		new byte[0],
		new byte[0],
		new byte[0],
		new byte[0],
		new byte[0],
		new byte[0],
		new byte[0],
		new byte[0]
	};

	private object usermodeLock = new object();

	private bool KBuserModeLock = true;

	private bool LBuserModeLock = true;

	private string AlphabetString = "";

	public bool ChangeEffect = true;

	private Thread SingleChangeThread;

	private object led_off_lock = new object();

	private static event RGBKB_Event_Handler m_Layout_Event_handler;

	public LM_ITE_RGB()
	{
		m_save_lighting_data.bSaved = false;
	}

	private void BatteryEable(bool Enable)
	{
		if (Enable)
		{
			BatteryEnable = Enable;
			Task.Run(delegate
			{
				for (int i = 0; i <= Convert.ToInt32(battry.GetCurrentBatteryLifePercent()); i++)
				{
					if (BatteryEnable)
					{
						IndicatorEffect(i.ToString());
					}
				}
			});
			battry.LifePercentChange -= Battry_LifePercentChange;
			battry.LifePercentChange += Battry_LifePercentChange;
			battry.BatteryStart();
		}
		else
		{
			RGB_S[] colorBuffer = new RGB_S[40];
			Set_ITE_Effect_Type_UserMode_Lightbar2(0, 0, colorBuffer, bRefresh: false, 3);
			BatteryEnable = false;
			battry.LifePercentChange -= Battry_LifePercentChange;
			battry.BatteryStop();
		}
	}

	private void Battry_LifePercentChange(object sender, EventArgs e)
	{
		LogCtrl.Write(sender.ToString());
		if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar2 && m_effect_type == 4)
		{
			IndicatorEffect(sender.ToString());
		}
	}

	public void IndicatorEffect(string percent)
	{
		int result = 100;
		int.TryParse(percent, out result);
		byte light = 50;
		bool bRefresh = false;
		RGB_S[] array = ((result >= 20 && result <= 60) ? PercentEffect(System.Drawing.Color.FromArgb(255, 255, 169, 0), System.Drawing.Color.FromArgb(255, 10, 10, 0), new RGB_S[7], result, 100.0) : ((result >= 20) ? PercentEffect(System.Drawing.Color.FromArgb(255, 0, 255, 0), System.Drawing.Color.FromArgb(255, 0, 10, 0), new RGB_S[7], result, 100.0) : PercentEffect(System.Drawing.Color.FromArgb(255, 255, 0, 0), System.Drawing.Color.FromArgb(255, 10, 0, 0), new RGB_S[7], result, 100.0)));
		RGB_S[] array2 = new RGB_S[40];
		for (int i = 0; i < array.Length; i++)
		{
			array2[i] = array[array.Length - i - 1];
		}
		Set_ITE_Effect_Type_UserMode_Lightbar2(light, 0, array2, bRefresh, 3);
	}

	public RGB_S[] PercentEffect(System.Drawing.Color foregroundColor, System.Drawing.Color backgroundColor, RGB_S[] keys, double value, double total, double flash_past = 0.0, bool flash_reversed = false, bool blink_background = false)
	{
		double num = value / total;
		if (num < 0.0)
		{
			num = 0.0;
		}
		else if (num > 1.0)
		{
			num = 1.0;
		}
		double num2 = num * (double)keys.Count();
		if (flash_past > 0.0 && ((flash_reversed && num >= flash_past) || (!flash_reversed && num <= flash_past)))
		{
			if (blink_background)
			{
				backgroundColor = ColorUtils.BlendColors(backgroundColor, System.Drawing.Color.FromArgb(0, 0, 0, 0), Math.Sin((double)Time.GetMillisecondsSinceEpoch() % 1000.0 / 1000.0 * Math.PI));
			}
			else
			{
				foregroundColor = ColorUtils.BlendColors(backgroundColor, foregroundColor, Math.Sin((double)Time.GetMillisecondsSinceEpoch() % 1000.0 / 1000.0 * Math.PI));
			}
		}
		for (int i = 0; i < keys.Count(); i++)
		{
			RGB_S currentColor = default(RGB_S);
			if (i == (int)num2)
			{
				double percent = num2 - (double)i;
				SetOneKey(ref currentColor, ColorUtils.BlendColors(backgroundColor, foregroundColor, percent));
			}
			else if (i < (int)num2)
			{
				SetOneKey(ref currentColor, foregroundColor);
			}
			else
			{
				SetOneKey(ref currentColor, backgroundColor);
			}
			keys[i] = currentColor;
		}
		return keys;
	}

	private void SetOneKey(ref RGB_S currentColor, System.Drawing.Color color)
	{
		currentColor.R = Convert.ToByte((double)(color.R * color.A) / 255.0);
		currentColor.G = Convert.ToByte((double)(color.G * color.A) / 255.0);
		currentColor.B = Convert.ToByte((double)(color.B * color.A) / 255.0);
	}

	public byte GetProjectID()
	{
		return m_Project_ID;
	}

	public LM_ITE_RGB GetLM_ITE_RGB_Self()
	{
		return this;
	}

	private void ScanCode_Hnadler(int scancode)
	{
		switch (scancode)
		{
		case 240:
		{
			m_light_lock = true;
			m_save_lighting_data.bSaved = true;
			m_save_lighting_data.save_power_status = RGBKB_PowerStatus.On;
			if (m_save_lighting_data.save_effect == 0)
			{
				bool bCircular2 = false;
				uint length2 = 7u;
				RGBKB_Color rGBKB_Color = new RGBKB_Color(bCircular2, length2);
				int num3 = 0;
				foreach (System.Windows.Media.Color defalutColor in DefalutColorList)
				{
					rGBKB_Color.ColorBuffer[num3].ID = (uint)num3;
					rGBKB_Color.ColorBuffer[num3].R = defalutColor.R;
					rGBKB_Color.ColorBuffer[num3].G = defalutColor.G;
					rGBKB_Color.ColorBuffer[num3].B = defalutColor.B;
					num3++;
				}
				Save_Lighting_Effect_Data(5, 3, 2, 0, rGBKB_Color, 0, null);
				Set_ITE_Effect_Type_FwMode(5, 3, 2, 0, 1, rGBKB_Color);
			}
			RGBKB_Event_Data event_data2 = default(RGBKB_Event_Data);
			byte light = 0;
			Get_ITE_Light_Value(ref light);
			event_data2.event_id = RGBKB_EventID.Brightness_update;
			event_data2.envet_data_len = 1u;
			event_data2.event_data = new byte[1];
			event_data2.event_data[0] = (byte)Translate_Layout_LightValue(light);
			LM_ITE_RGB.m_Layout_Event_handler(event_data2);
			Log.s(LOG_LEVEL.TRACE, string.Format("ITE_0x0F level :  ", event_data2.event_data[0]));
			if (m_effect_type == 3)
			{
				m_ap_effect_data.save_light = light;
			}
			else if (m_effect_type == 4)
			{
				m_ap_effect_data.save_light = light;
			}
			else
			{
				m_save_lighting_data.save_light = light;
			}
			m_light_lock = false;
			break;
		}
		case 177:
		case 178:
		{
			m_save_lighting_data.bSaved = true;
			m_save_lighting_data.save_power_status = RGBKB_PowerStatus.On;
			if (m_save_lighting_data.save_effect == 0)
			{
				bool bCircular = false;
				uint length = 7u;
				RGBKB_Color save_layout_color = new RGBKB_Color(bCircular, length);
				int num = 0;
				foreach (System.Windows.Media.Color defalutColor2 in DefalutColorList)
				{
					save_layout_color.ColorBuffer[num].ID = (uint)num;
					save_layout_color.ColorBuffer[num].R = defalutColor2.R;
					save_layout_color.ColorBuffer[num].G = defalutColor2.G;
					save_layout_color.ColorBuffer[num].B = defalutColor2.B;
					num++;
				}
				Save_Lighting_Effect_Data(5, 3, 2, 0, save_layout_color, 0, null);
			}
			uint num2 = Translate_Layout_LightValue(m_save_lighting_data.save_light);
			Log.s(LOG_LEVEL.TRACE, $"0x0B1 ori {num2.ToString()} ");
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
			if (m_save_lighting_data.bSaved && flag)
			{
				uint layoutLight = Convert.ToUInt32(num2);
				m_save_lighting_data.save_light = Translate_ITE_LightValue(layoutLight);
				if (m_save_lighting_data.save_power_status == RGBKB_PowerStatus.On || m_save_lighting_data.save_power_status == RGBKB_PowerStatus.Lighting_on)
				{
					if (Ver_High >= 18 && Ver_Low >= 7)
					{
						HID_Set_Brightness_Level_09H(m_save_lighting_data.save_light);
					}
					else
					{
						Set_Lighting_Effect(2, m_save_lighting_data.save_effect, m_save_lighting_data.save_light, m_save_lighting_data.save_speed, m_save_lighting_data.save_direction, 0, m_save_lighting_data.save_layout_color);
					}
				}
			}
			RGBKB_Event_Data event_data = new RGBKB_Event_Data
			{
				event_id = RGBKB_EventID.Brightness_update,
				envet_data_len = 1u,
				event_data = new byte[1]
			};
			event_data.event_data[0] = (byte)num2;
			LM_ITE_RGB.m_Layout_Event_handler(event_data);
			Log.s(LOG_LEVEL.TRACE, string.Format("osd ", m_save_lighting_data.save_power_status.ToString()));
			break;
		}
		}
	}

	private void Light_Lock()
	{
		if (m_light_lock)
		{
			uint num = 10u;
			while (m_light_lock && num != 0)
			{
				Thread.Sleep(5);
				num--;
			}
		}
	}

	private void AP_Effect_Task()
	{
		RGB_S[] array = new RGB_S[3];
		RGB_S[] array2 = new RGB_S[126];
		byte save_light = m_ap_effect_data.save_light;
		bool bRefresh = true;
		uint num = 0u;
		int num2 = 0;
		float num3 = 1f;
		RGB_S[] colorBuffer = m_ap_effect_data.save_layout_color.ColorBuffer;
		List<LEDActor> list = new List<LEDActor>();
		int num4 = 1;
		foreach (RGB_S item in m_ap_effect_data.save_layout_color.ColorBuffer.Take(23))
		{
			LEDActor lEDActor = new LEDActor(num4, 0);
			lEDActor.ActorName = "ledact " + num4;
			lEDActor.SetColor(item);
			list.Add(lEDActor);
			num4++;
		}
		List<LEDActor> list2 = new List<LEDActor>();
		int num5 = 0;
		new Random();
		foreach (LEDActor item2 in list)
		{
			if (Actor.CheckColor(item2))
			{
				int direction = ((num5 % 2 == 0) ? 1 : (-1));
				item2.setDirection(direction);
				list2.Add(item2);
				num5++;
			}
		}
		LEDActor lEDActor2 = new LEDActor(-1, 0);
		lEDActor2.SetColor(new RGB_S(0u, byte.MaxValue, 0, 0));
		LEDActor lEDActor3 = new LEDActor(23, 0);
		lEDActor3.SetColor(new RGB_S(0u, byte.MaxValue, 0, 0));
		while (!m_ap_effect_task_stop)
		{
			if (save_light != m_ap_effect_data.save_light)
			{
				save_light = m_ap_effect_data.save_light;
				bRefresh = true;
			}
			if (m_ap_effect_data.save_effect == 25)
			{
				if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar)
				{
					foreach (LEDActor ecahActor in list)
					{
						if (Actor.CheckColor(ecahActor))
						{
							ecahActor.MoveByDirection();
							int index = list2.FindIndex((LEDActor n) => n.Equals(ecahActor));
							if (CheckCollsion(list2[index], list2))
							{
								ecahActor.DirectionReverse();
								num3 *= 0.9f;
							}
							if (Actor.IsCollision(ecahActor, lEDActor2))
							{
								ecahActor.setDirection(1);
							}
							if (Actor.IsCollision(ecahActor, lEDActor3))
							{
								ecahActor.setDirection(-1);
							}
							ecahActor.Update();
						}
					}
					List<RGB_S> list3 = new List<RGB_S>();
					foreach (LEDActor item3 in list)
					{
						_ = item3;
						list3.Add(default(RGB_S));
					}
					foreach (LEDActor item4 in list)
					{
						if (item4.PositionBounds.Right < list.Count && item4.PositionBounds.Right > -1 && Actor.CheckColor(item4))
						{
							list3[item4.PositionBounds.Right] = item4.ActorColor;
						}
					}
					list3.ToArray();
					Set_ITE_Effect_Type_UserMode_Lightbar12h(m_ap_effect_data.save_light, 0, list3.ToArray(), bRefresh: false);
					float num6 = 50f * num3;
					if (num6 < 30f)
					{
						num3 = 1f;
					}
					Thread.Sleep(Convert.ToInt32(num6));
					num++;
					if (m_ap_effect_data.save_effect != 25)
					{
						num = 0u;
					}
				}
			}
			else if (m_ap_effect_data.save_effect == 24)
			{
				Random random = new Random();
				List<RGB_S> list4 = new List<RGB_S>();
				for (int num7 = 0; num7 < colorBuffer.Count(); num7++)
				{
					double num8 = (double)random.Next(100) * 0.01;
					list4.Add(new RGB_S
					{
						R = Convert.ToByte((double)(int)colorBuffer[num7].R * num8),
						G = Convert.ToByte((double)(int)colorBuffer[num7].G * num8),
						B = Convert.ToByte((double)(int)colorBuffer[num7].B * num8)
					});
				}
				Set_ITE_Effect_Type_UserMode_Lightbar12h(m_ap_effect_data.save_light, 0, list4.ToArray(), bRefresh: false);
				Thread.Sleep(150);
				num++;
				if (m_ap_effect_data.save_effect != 24)
				{
					num = 0u;
				}
			}
			else if (m_ap_effect_data.save_effect == 15)
			{
				if (num == 7)
				{
					num = 0u;
				}
				array[0].R = m_ap_effect_data.save_layout_color.ColorBuffer[num].R;
				array[0].G = m_ap_effect_data.save_layout_color.ColorBuffer[num].G;
				array[0].B = m_ap_effect_data.save_layout_color.ColorBuffer[num].B;
				Set_ITE_Effect_Type_StaticMode(m_ap_effect_data.save_light, 0, array, bRefresh);
				Thread.Sleep(50 * m_ap_effect_data.save_speed);
				num++;
				if (m_ap_effect_data.save_effect != 15)
				{
					num = 0u;
				}
			}
			else if (m_ap_effect_data.save_effect == 23)
			{
				int num9 = 19 - ColRightShift;
				char[] array3 = AlphabetString?.Trim().ToUpperInvariant().ToArray();
				if (array3 != null)
				{
					if (num == num9)
					{
						num = 0u;
						num2++;
					}
					if (num2 >= array3.Count())
					{
						num2 = 0;
					}
					if (array3.Count() > 0)
					{
						AlphabetEffect alphabetEffect = new AlphabetEffect(array3[num2], m_ap_effect_data.save_layout_color.ColorBuffer, num);
						alphabetEffect.SetShift(Convert.ToInt32(num % num9));
						array2 = alphabetEffect.GetAlphbetEffect();
						Set_ITE_Effect_Type_UserMode(m_ap_effect_data.save_light, 0, array2, bRefresh);
						Thread.Sleep(80 * m_ap_effect_data.save_speed);
						num++;
						if (m_ap_effect_data.save_effect != 23)
						{
							num = 0u;
							num2 = 0;
						}
					}
				}
			}
			else if (m_ap_effect_data.save_effect == 13)
			{
				array[0].R = m_ap_effect_data.save_layout_color.ColorBuffer[0].R;
				array[0].G = m_ap_effect_data.save_layout_color.ColorBuffer[0].G;
				array[0].B = m_ap_effect_data.save_layout_color.ColorBuffer[0].B;
				array[1].R = m_ap_effect_data.save_layout_color.ColorBuffer[1].R;
				array[1].G = m_ap_effect_data.save_layout_color.ColorBuffer[1].G;
				array[1].B = m_ap_effect_data.save_layout_color.ColorBuffer[1].B;
				array[2].R = m_ap_effect_data.save_layout_color.ColorBuffer[2].R;
				array[2].G = m_ap_effect_data.save_layout_color.ColorBuffer[2].G;
				array[2].B = m_ap_effect_data.save_layout_color.ColorBuffer[2].B;
				int num10 = 0;
				if (ColRightShift != 0)
				{
					num10 = ColRightShift + 3;
				}
				int num11 = 20 - num10;
				if (num == num11)
				{
					num = 0u;
				}
				for (uint num12 = 0u; num12 < 126; num12++)
				{
					array2[num12].ID = num12;
					array2[num12].R = 0;
					array2[num12].G = 0;
					array2[num12].B = 0;
				}
				if (num < num11 / 2)
				{
					array2[num].R = array[0].R;
					array2[num].G = array[0].G;
					array2[num].B = array[0].B;
					array2[1 + num].R = array[0].R;
					array2[1 + num].G = array[0].G;
					array2[1 + num].B = array[0].B;
					array2[21 + num].R = array[0].R;
					array2[21 + num].G = array[0].G;
					array2[21 + num].B = array[0].B;
					array2[22 + num].R = array[0].R;
					array2[22 + num].G = array[0].G;
					array2[22 + num].B = array[0].B;
					array2[42 + num].R = array[0].R;
					array2[42 + num].G = array[0].G;
					array2[42 + num].B = array[0].B;
					array2[43 + num].R = array[0].R;
					array2[43 + num].G = array[0].G;
					array2[43 + num].B = array[0].B;
					array2[63 + num].R = array[0].R;
					array2[63 + num].G = array[0].G;
					array2[63 + num].B = array[0].B;
					array2[64 + num].R = array[0].R;
					array2[64 + num].G = array[0].G;
					array2[64 + num].B = array[0].B;
					array2[84 + num].R = array[0].R;
					array2[84 + num].G = array[0].G;
					array2[84 + num].B = array[0].B;
					array2[85 + num].R = array[0].R;
					array2[85 + num].G = array[0].G;
					array2[85 + num].B = array[0].B;
					array2[105 + num].R = array[0].R;
					array2[105 + num].G = array[0].G;
					array2[105 + num].B = array[0].B;
					array2[106 + num].R = array[0].R;
					array2[106 + num].G = array[0].G;
					array2[106 + num].B = array[0].B;
					array2[20 - num10 - num].R = array[1].R;
					array2[20 - num10 - num].G = array[1].G;
					array2[20 - num10 - num].B = array[1].B;
					array2[19 - num10 - num].R = array[1].R;
					array2[19 - num10 - num].G = array[1].G;
					array2[19 - num10 - num].B = array[1].B;
					array2[41 - num10 - num].R = array[1].R;
					array2[41 - num10 - num].G = array[1].G;
					array2[41 - num10 - num].B = array[1].B;
					array2[40 - num10 - num].R = array[1].R;
					array2[40 - num10 - num].G = array[1].G;
					array2[40 - num10 - num].B = array[1].B;
					array2[62 - num10 - num].R = array[1].R;
					array2[62 - num10 - num].G = array[1].G;
					array2[62 - num10 - num].B = array[1].B;
					array2[61 - num10 - num].R = array[1].R;
					array2[61 - num10 - num].G = array[1].G;
					array2[61 - num10 - num].B = array[1].B;
					array2[83 - num10 - num].R = array[1].R;
					array2[83 - num10 - num].G = array[1].G;
					array2[83 - num10 - num].B = array[1].B;
					array2[82 - num10 - num].R = array[1].R;
					array2[82 - num10 - num].G = array[1].G;
					array2[82 - num10 - num].B = array[1].B;
					array2[104 - num10 - num].R = array[1].R;
					array2[104 - num10 - num].G = array[1].G;
					array2[104 - num10 - num].B = array[1].B;
					array2[103 - num10 - num].R = array[1].R;
					array2[103 - num10 - num].G = array[1].G;
					array2[103 - num10 - num].B = array[1].B;
					array2[125 - num10 - num].R = array[1].R;
					array2[125 - num10 - num].G = array[1].G;
					array2[125 - num10 - num].B = array[1].B;
					array2[124 - num10 - num].R = array[1].R;
					array2[124 - num10 - num].G = array[1].G;
					array2[124 - num10 - num].B = array[1].B;
				}
				else
				{
					uint num13 = num - 10;
					if (ColRightShift != 0)
					{
						num13 = num - 4;
					}
					array2[10 - num13].R = array[2].R;
					array2[10 - num13].G = array[2].G;
					array2[10 - num13].B = array[2].B;
					array2[9 - num13].R = array[2].R;
					array2[9 - num13].G = array[2].G;
					array2[9 - num13].B = array[2].B;
					array2[31 - num13].R = array[2].R;
					array2[31 - num13].G = array[2].G;
					array2[31 - num13].B = array[2].B;
					array2[30 - num13].R = array[2].R;
					array2[30 - num13].G = array[2].G;
					array2[30 - num13].B = array[2].B;
					array2[52 - num13].R = array[2].R;
					array2[52 - num13].G = array[2].G;
					array2[52 - num13].B = array[2].B;
					array2[51 - num13].R = array[2].R;
					array2[51 - num13].G = array[2].G;
					array2[51 - num13].B = array[2].B;
					array2[73 - num13].R = array[2].R;
					array2[73 - num13].G = array[2].G;
					array2[73 - num13].B = array[2].B;
					array2[72 - num13].R = array[2].R;
					array2[72 - num13].G = array[2].G;
					array2[72 - num13].B = array[2].B;
					array2[94 - num13].R = array[2].R;
					array2[94 - num13].G = array[2].G;
					array2[94 - num13].B = array[2].B;
					array2[93 - num13].R = array[2].R;
					array2[93 - num13].G = array[2].G;
					array2[93 - num13].B = array[2].B;
					array2[115 - num13].R = array[2].R;
					array2[115 - num13].G = array[2].G;
					array2[115 - num13].B = array[2].B;
					array2[114 - num13].R = array[2].R;
					array2[114 - num13].G = array[2].G;
					array2[114 - num13].B = array[2].B;
					array2[10 - num10 + num13].R = array[2].R;
					array2[10 - num10 + num13].G = array[2].G;
					array2[10 - num10 + num13].B = array[2].B;
					array2[9 - num10 + num13].R = array[2].R;
					array2[9 - num10 + num13].G = array[2].G;
					array2[9 - num10 + num13].B = array[2].B;
					array2[31 - num10 + num13].R = array[2].R;
					array2[31 - num10 + num13].G = array[2].G;
					array2[31 - num10 + num13].B = array[2].B;
					array2[30 - num10 + num13].R = array[2].R;
					array2[30 - num10 + num13].G = array[2].G;
					array2[30 - num10 + num13].B = array[2].B;
					array2[52 - num10 + num13].R = array[2].R;
					array2[52 - num10 + num13].G = array[2].G;
					array2[52 - num10 + num13].B = array[2].B;
					array2[51 - num10 + num13].R = array[2].R;
					array2[51 - num10 + num13].G = array[2].G;
					array2[51 - num10 + num13].B = array[2].B;
					array2[73 - num10 + num13].R = array[2].R;
					array2[73 - num10 + num13].G = array[2].G;
					array2[73 - num10 + num13].B = array[2].B;
					array2[72 - num10 + num13].R = array[2].R;
					array2[72 - num10 + num13].G = array[2].G;
					array2[72 - num10 + num13].B = array[2].B;
					array2[94 - num10 + num13].R = array[2].R;
					array2[94 - num10 + num13].G = array[2].G;
					array2[94 - num10 + num13].B = array[2].B;
					array2[93 - num10 + num13].R = array[2].R;
					array2[93 - num10 + num13].G = array[2].G;
					array2[93 - num10 + num13].B = array[2].B;
					array2[115 - num10 + num13].R = array[2].R;
					array2[115 - num10 + num13].G = array[2].G;
					array2[115 - num10 + num13].B = array[2].B;
					array2[114 - num10 + num13].R = array[2].R;
					array2[114 - num10 + num13].G = array[2].G;
					array2[114 - num10 + num13].B = array[2].B;
				}
				Set_ITE_Effect_Type_UserMode(m_ap_effect_data.save_light, 0, array2, bRefresh);
				Thread.Sleep(20 * m_ap_effect_data.save_speed);
				num++;
				if (m_ap_effect_data.save_effect != 13)
				{
					num = 0u;
				}
			}
			else if (m_ap_effect_data.save_effect == 12)
			{
				array[0].R = m_ap_effect_data.save_layout_color.ColorBuffer[0].R;
				array[0].G = m_ap_effect_data.save_layout_color.ColorBuffer[0].G;
				array[0].B = m_ap_effect_data.save_layout_color.ColorBuffer[0].B;
				array[1].R = m_ap_effect_data.save_layout_color.ColorBuffer[1].R;
				array[1].G = m_ap_effect_data.save_layout_color.ColorBuffer[1].G;
				array[1].B = m_ap_effect_data.save_layout_color.ColorBuffer[1].B;
				array[2].R = m_ap_effect_data.save_layout_color.ColorBuffer[2].R;
				array[2].G = m_ap_effect_data.save_layout_color.ColorBuffer[2].G;
				array[2].B = m_ap_effect_data.save_layout_color.ColorBuffer[2].B;
				for (uint num14 = 0u; num14 < 126; num14++)
				{
					array2[num14].ID = num14;
					array2[num14].R = 0;
					array2[num14].G = 0;
					array2[num14].B = 0;
				}
				uint num15 = 15u;
				if (ColRightShift != 0)
				{
					_ = ColRightShift;
					num15 = 15 - Convert.ToUInt32(ColRightShift + 1);
				}
				uint num16 = num % num15;
				uint num17 = num / 15;
				byte r = array[num17].R;
				byte g = array[num17].G;
				byte b = array[num17].B;
				array2[52 - ColShift].R = r;
				array2[52 - ColShift].G = g;
				array2[52 - ColShift].B = b;
				switch (num16)
				{
				case 0u:
					array2[0].R = (array2[105].R = r);
					array2[0].G = (array2[105].G = g);
					array2[0].B = (array2[105].B = b);
					array2[20].R = (array2[125].R = r);
					array2[20].G = (array2[125].G = g);
					array2[20].B = (array2[125].B = b);
					break;
				case 1u:
					array2[1].R = (array2[21].R = (array2[84].R = (array2[106].R = r)));
					array2[1].G = (array2[21].G = (array2[84].G = (array2[106].G = g)));
					array2[1].B = (array2[21].B = (array2[84].B = (array2[106].B = b)));
					array2[19 - ColRightShift].R = (array2[41 - ColRightShift].R = (array2[104 - ColRightShift].R = (array2[124 - ColRightShift].R = r)));
					array2[19 - ColRightShift].G = (array2[41 - ColRightShift].G = (array2[104 - ColRightShift].G = (array2[124 - ColRightShift].G = g)));
					array2[19 - ColRightShift].B = (array2[41 - ColRightShift].B = (array2[104 - ColRightShift].B = (array2[124 - ColRightShift].B = b)));
					break;
				case 2u:
					array2[2].R = (array2[21].R = (array2[22].R = (array2[63].R = (array2[84].R = (array2[85].R = (array2[107].R = r))))));
					array2[2].G = (array2[21].G = (array2[22].G = (array2[63].G = (array2[84].G = (array2[85].G = (array2[107].G = g))))));
					array2[2].B = (array2[21].B = (array2[22].B = (array2[63].B = (array2[84].B = (array2[85].B = (array2[107].B = b))))));
					array2[18 - ColRightShift].R = (array2[40 - ColRightShift].R = (array2[41 - ColRightShift].R = (array2[83 - ColRightShift].R = (array2[103 - ColRightShift].R = (array2[104 - ColRightShift].R = (array2[123 - ColRightShift].R = r))))));
					array2[18 - ColRightShift].G = (array2[40 - ColRightShift].G = (array2[41 - ColRightShift].G = (array2[83 - ColRightShift].G = (array2[103 - ColRightShift].G = (array2[104 - ColRightShift].G = (array2[123 - ColRightShift].G = g))))));
					array2[18 - ColRightShift].B = (array2[40 - ColRightShift].B = (array2[41 - ColRightShift].B = (array2[83 - ColRightShift].B = (array2[103 - ColRightShift].B = (array2[104 - ColRightShift].B = (array2[123 - ColRightShift].B = b))))));
					break;
				case 3u:
					array2[3].R = (array2[22].R = (array2[23].R = (array2[42].R = (array2[63].R = (array2[64].R = (array2[85].R = (array2[86].R = (array2[108].R = r))))))));
					array2[3].G = (array2[22].G = (array2[23].G = (array2[42].G = (array2[63].G = (array2[64].G = (array2[85].G = (array2[86].G = (array2[108].G = g))))))));
					array2[3].B = (array2[22].B = (array2[23].B = (array2[42].B = (array2[63].B = (array2[64].B = (array2[85].B = (array2[86].B = (array2[108].B = b))))))));
					array2[17 - ColRightShift].R = (array2[38 - ColRightShift].R = (array2[39 - ColRightShift].R = (array2[62 - ColRightShift].R = (array2[82 - ColRightShift].R = (array2[83 - ColRightShift].R = (array2[102 - ColRightShift].R = (array2[103 - ColRightShift].R = (array2[122 - ColRightShift].R = r))))))));
					array2[17 - ColRightShift].G = (array2[38 - ColRightShift].G = (array2[39 - ColRightShift].G = (array2[62 - ColRightShift].G = (array2[82 - ColRightShift].G = (array2[83 - ColRightShift].G = (array2[102 - ColRightShift].G = (array2[103 - ColRightShift].G = (array2[122 - ColRightShift].G = g))))))));
					array2[17 - ColRightShift].B = (array2[38 - ColRightShift].B = (array2[39 - ColRightShift].B = (array2[62 - ColRightShift].B = (array2[82 - ColRightShift].B = (array2[83 - ColRightShift].B = (array2[102 - ColRightShift].B = (array2[103 - ColRightShift].B = (array2[122 - ColRightShift].B = b))))))));
					break;
				case 4u:
					array2[4].R = (array2[23].R = (array2[24].R = (array2[42].R = (array2[43].R = (array2[64].R = (array2[65].R = (array2[86].R = (array2[87].R = (array2[109].R = r)))))))));
					array2[4].G = (array2[23].G = (array2[24].G = (array2[42].G = (array2[43].G = (array2[64].G = (array2[65].G = (array2[86].G = (array2[87].G = (array2[109].G = g)))))))));
					array2[4].B = (array2[23].B = (array2[24].B = (array2[42].B = (array2[43].B = (array2[64].B = (array2[65].B = (array2[86].B = (array2[87].B = (array2[109].B = b)))))))));
					array2[16 - ColRightShift].R = (array2[37 - ColRightShift].R = (array2[38 - ColRightShift].R = (array2[61 - ColRightShift].R = (array2[62 - ColRightShift].R = (array2[81 - ColRightShift].R = (array2[82 - ColRightShift].R = (array2[101 - ColRightShift].R = (array2[102 - ColRightShift].R = (array2[121 - ColRightShift].R = r)))))))));
					array2[16 - ColRightShift].G = (array2[37 - ColRightShift].G = (array2[38 - ColRightShift].G = (array2[61 - ColRightShift].G = (array2[62 - ColRightShift].G = (array2[81 - ColRightShift].G = (array2[82 - ColRightShift].G = (array2[101 - ColRightShift].G = (array2[102 - ColRightShift].G = (array2[121 - ColRightShift].G = g)))))))));
					array2[16 - ColRightShift].B = (array2[37 - ColRightShift].B = (array2[38 - ColRightShift].B = (array2[61 - ColRightShift].B = (array2[62 - ColRightShift].B = (array2[81 - ColRightShift].B = (array2[82 - ColRightShift].B = (array2[101 - ColRightShift].B = (array2[102 - ColRightShift].B = (array2[121 - ColRightShift].B = b)))))))));
					break;
				case 5u:
					array2[5].R = (array2[24].R = (array2[25].R = (array2[43].R = (array2[44].R = (array2[65].R = (array2[66].R = (array2[87].R = (array2[88].R = (array2[110].R = r)))))))));
					array2[5].G = (array2[24].G = (array2[25].G = (array2[43].G = (array2[44].G = (array2[65].G = (array2[66].G = (array2[87].G = (array2[88].G = (array2[110].G = g)))))))));
					array2[5].B = (array2[24].B = (array2[25].B = (array2[43].B = (array2[44].B = (array2[65].B = (array2[66].B = (array2[87].B = (array2[88].B = (array2[110].B = b)))))))));
					array2[15 - ColRightShift].R = (array2[36 - ColRightShift].R = (array2[37 - ColRightShift].R = (array2[60 - ColRightShift].R = (array2[61 - ColRightShift].R = (array2[80 - ColRightShift].R = (array2[81 - ColRightShift].R = (array2[100 - ColRightShift].R = (array2[101 - ColRightShift].R = (array2[120 - ColRightShift].R = r)))))))));
					array2[15 - ColRightShift].G = (array2[36 - ColRightShift].G = (array2[37 - ColRightShift].G = (array2[60 - ColRightShift].G = (array2[61 - ColRightShift].G = (array2[80 - ColRightShift].G = (array2[81 - ColRightShift].G = (array2[100 - ColRightShift].G = (array2[101 - ColRightShift].G = (array2[120 - ColRightShift].G = g)))))))));
					array2[15 - ColRightShift].B = (array2[36 - ColRightShift].B = (array2[37 - ColRightShift].B = (array2[60 - ColRightShift].B = (array2[61 - ColRightShift].B = (array2[80 - ColRightShift].B = (array2[81 - ColRightShift].B = (array2[100 - ColRightShift].B = (array2[101 - ColRightShift].B = (array2[120 - ColRightShift].B = b)))))))));
					break;
				case 6u:
					array2[6].R = (array2[25].R = (array2[26].R = (array2[44].R = (array2[45].R = (array2[66].R = (array2[67].R = (array2[88].R = (array2[89].R = (array2[111].R = r)))))))));
					array2[6].G = (array2[25].G = (array2[26].G = (array2[44].G = (array2[45].G = (array2[66].G = (array2[67].G = (array2[88].G = (array2[89].G = (array2[111].G = g)))))))));
					array2[6].B = (array2[25].B = (array2[26].B = (array2[44].B = (array2[45].B = (array2[66].B = (array2[67].B = (array2[88].B = (array2[89].B = (array2[111].B = b)))))))));
					array2[14 - ColRightShift].R = (array2[35 - ColRightShift].R = (array2[36 - ColRightShift].R = (array2[59 - ColRightShift].R = (array2[60 - ColRightShift].R = (array2[79 - ColRightShift].R = (array2[80 - ColRightShift].R = (array2[99 - ColRightShift].R = (array2[100 - ColRightShift].R = (array2[119 - ColRightShift].R = r)))))))));
					array2[14 - ColRightShift].G = (array2[35 - ColRightShift].G = (array2[36 - ColRightShift].G = (array2[59 - ColRightShift].G = (array2[60 - ColRightShift].G = (array2[79 - ColRightShift].G = (array2[80 - ColRightShift].G = (array2[99 - ColRightShift].G = (array2[100 - ColRightShift].G = (array2[119 - ColRightShift].G = g)))))))));
					array2[14 - ColRightShift].B = (array2[35 - ColRightShift].B = (array2[36 - ColRightShift].B = (array2[59 - ColRightShift].B = (array2[60 - ColRightShift].B = (array2[79 - ColRightShift].B = (array2[80 - ColRightShift].B = (array2[99 - ColRightShift].B = (array2[100 - ColRightShift].B = (array2[119 - ColRightShift].B = b)))))))));
					break;
				case 7u:
					array2[7].R = (array2[26].R = (array2[27].R = (array2[45].R = (array2[46].R = (array2[67].R = (array2[68].R = (array2[89].R = (array2[90].R = (array2[112].R = r)))))))));
					array2[7].G = (array2[26].G = (array2[27].G = (array2[45].G = (array2[46].G = (array2[67].G = (array2[68].G = (array2[89].G = (array2[90].G = (array2[112].G = g)))))))));
					array2[7].B = (array2[26].B = (array2[27].B = (array2[45].B = (array2[46].B = (array2[67].B = (array2[68].B = (array2[89].B = (array2[90].B = (array2[112].B = b)))))))));
					array2[13 - ColRightShift].R = (array2[34 - ColRightShift].R = (array2[35 - ColRightShift].R = (array2[58 - ColRightShift].R = (array2[59 - ColRightShift].R = (array2[78 - ColRightShift].R = (array2[79 - ColRightShift].R = (array2[98 - ColRightShift].R = (array2[99 - ColRightShift].R = (array2[118 - ColRightShift].R = r)))))))));
					array2[13 - ColRightShift].G = (array2[34 - ColRightShift].G = (array2[35 - ColRightShift].G = (array2[58 - ColRightShift].G = (array2[59 - ColRightShift].G = (array2[78 - ColRightShift].G = (array2[79 - ColRightShift].G = (array2[98 - ColRightShift].G = (array2[99 - ColRightShift].G = (array2[118 - ColRightShift].G = g)))))))));
					array2[13 - ColRightShift].B = (array2[34 - ColRightShift].B = (array2[35 - ColRightShift].B = (array2[58 - ColRightShift].B = (array2[59 - ColRightShift].B = (array2[78 - ColRightShift].B = (array2[79 - ColRightShift].B = (array2[98 - ColRightShift].B = (array2[99 - ColRightShift].B = (array2[118 - ColRightShift].B = b)))))))));
					break;
				case 8u:
					array2[8].R = (array2[27].R = (array2[28].R = (array2[46].R = (array2[47].R = (array2[68].R = (array2[69].R = (array2[90].R = (array2[91].R = (array2[113].R = r)))))))));
					array2[8].G = (array2[27].G = (array2[28].G = (array2[46].G = (array2[47].G = (array2[68].G = (array2[69].G = (array2[90].G = (array2[91].G = (array2[113].G = g)))))))));
					array2[8].B = (array2[27].B = (array2[28].B = (array2[46].B = (array2[47].B = (array2[68].B = (array2[69].B = (array2[90].B = (array2[91].B = (array2[113].B = b)))))))));
					array2[12 - ColRightShift].R = (array2[33 - ColRightShift].R = (array2[34 - ColRightShift].R = (array2[57 - ColRightShift].R = (array2[58 - ColRightShift].R = (array2[77 - ColRightShift].R = (array2[78 - ColRightShift].R = (array2[97 - ColRightShift].R = (array2[98 - ColRightShift].R = (array2[117 - ColRightShift].R = r)))))))));
					array2[12 - ColRightShift].G = (array2[33 - ColRightShift].G = (array2[34 - ColRightShift].G = (array2[57 - ColRightShift].G = (array2[58 - ColRightShift].G = (array2[77 - ColRightShift].G = (array2[78 - ColRightShift].G = (array2[97 - ColRightShift].G = (array2[98 - ColRightShift].G = (array2[117 - ColRightShift].G = g)))))))));
					array2[12 - ColRightShift].B = (array2[33 - ColRightShift].B = (array2[34 - ColRightShift].B = (array2[57 - ColRightShift].B = (array2[58 - ColRightShift].B = (array2[77 - ColRightShift].B = (array2[78 - ColRightShift].B = (array2[97 - ColRightShift].B = (array2[98 - ColRightShift].B = (array2[117 - ColRightShift].B = b)))))))));
					break;
				case 9u:
					array2[9].R = (array2[28].R = (array2[29].R = (array2[47].R = (array2[48].R = (array2[69].R = (array2[70].R = (array2[91].R = (array2[92].R = (array2[114].R = r)))))))));
					array2[9].G = (array2[28].G = (array2[29].G = (array2[47].G = (array2[48].G = (array2[69].G = (array2[70].G = (array2[91].G = (array2[92].G = (array2[114].G = g)))))))));
					array2[9].B = (array2[28].B = (array2[29].B = (array2[47].B = (array2[48].B = (array2[69].B = (array2[70].B = (array2[91].B = (array2[92].B = (array2[114].B = b)))))))));
					array2[11 - ColRightShift].R = (array2[32 - ColRightShift].R = (array2[33 - ColRightShift].R = (array2[56 - ColRightShift].R = (array2[57 - ColRightShift].R = (array2[76 - ColRightShift].R = (array2[77 - ColRightShift].R = (array2[96 - ColRightShift].R = (array2[97 - ColRightShift].R = (array2[116 - ColRightShift].R = r)))))))));
					array2[11 - ColRightShift].G = (array2[32 - ColRightShift].G = (array2[33 - ColRightShift].G = (array2[56 - ColRightShift].G = (array2[57 - ColRightShift].G = (array2[76 - ColRightShift].G = (array2[77 - ColRightShift].G = (array2[96 - ColRightShift].G = (array2[97 - ColRightShift].G = (array2[116 - ColRightShift].G = g)))))))));
					array2[11 - ColRightShift].B = (array2[32 - ColRightShift].B = (array2[33 - ColRightShift].B = (array2[56 - ColRightShift].B = (array2[57 - ColRightShift].B = (array2[76 - ColRightShift].B = (array2[77 - ColRightShift].B = (array2[96 - ColRightShift].B = (array2[97 - ColRightShift].B = (array2[116 - ColRightShift].B = b)))))))));
					break;
				case 10u:
					array2[10].R = (array2[29].R = (array2[30].R = (array2[48].R = (array2[49].R = (array2[70].R = (array2[71].R = (array2[92].R = (array2[93].R = r))))))));
					array2[10].G = (array2[29].G = (array2[30].G = (array2[48].G = (array2[49].G = (array2[70].G = (array2[71].G = (array2[92].G = (array2[93].G = g))))))));
					array2[10].B = (array2[29].B = (array2[30].B = (array2[48].B = (array2[49].B = (array2[70].B = (array2[71].B = (array2[92].B = (array2[93].B = b))))))));
					array2[31 - ColRightShift].R = (array2[32 - ColRightShift].R = (array2[55 - ColRightShift].R = (array2[56 - ColRightShift].R = (array2[75 - ColRightShift].R = (array2[76 - ColRightShift].R = (array2[95 - ColRightShift].R = (array2[96 - ColRightShift].R = r)))))));
					array2[31 - ColRightShift].G = (array2[32 - ColRightShift].G = (array2[55 - ColRightShift].G = (array2[56 - ColRightShift].G = (array2[75 - ColRightShift].G = (array2[76 - ColRightShift].G = (array2[95 - ColRightShift].G = (array2[96 - ColRightShift].G = g)))))));
					array2[31 - ColRightShift].B = (array2[32 - ColRightShift].B = (array2[55 - ColRightShift].B = (array2[56 - ColRightShift].B = (array2[75 - ColRightShift].B = (array2[76 - ColRightShift].B = (array2[95 - ColRightShift].B = (array2[96 - ColRightShift].B = b)))))));
					break;
				case 11u:
					array2[30].R = (array2[49].R = (array2[50].R = (array2[71].R = (array2[72].R = (array2[93].R = r)))));
					array2[30].G = (array2[49].G = (array2[50].G = (array2[71].G = (array2[72].G = (array2[93].G = g)))));
					array2[30].B = (array2[49].B = (array2[50].B = (array2[71].B = (array2[72].B = (array2[93].B = b)))));
					array2[31 - ColRightShift].R = (array2[54 - ColRightShift].R = (array2[55 - ColRightShift].R = (array2[74 - ColRightShift].R = (array2[75 - ColRightShift].R = (array2[94 - ColRightShift].R = r)))));
					array2[31 - ColRightShift].G = (array2[54 - ColRightShift].G = (array2[55 - ColRightShift].G = (array2[74 - ColRightShift].G = (array2[75 - ColRightShift].G = (array2[94 - ColRightShift].G = g)))));
					array2[31 - ColRightShift].B = (array2[54 - ColRightShift].B = (array2[55 - ColRightShift].B = (array2[74 - ColRightShift].B = (array2[75 - ColRightShift].B = (array2[94 - ColRightShift].B = b)))));
					break;
				case 12u:
					array2[50].R = (array2[51].R = (array2[72].R = r));
					array2[50].G = (array2[51].G = (array2[72].G = g));
					array2[50].B = (array2[51].B = (array2[72].B = b));
					array2[53 - ColRightShift].R = (array2[54 - ColRightShift].R = (array2[73 - ColRightShift].R = r));
					array2[53 - ColRightShift].G = (array2[54 - ColRightShift].G = (array2[73 - ColRightShift].G = g));
					array2[53 - ColRightShift].B = (array2[54 - ColRightShift].B = (array2[73 - ColRightShift].B = b));
					break;
				case 13u:
					array2[51].R = (array2[52].R = r);
					array2[51].G = (array2[52].G = g);
					array2[51].B = (array2[52].B = b);
					array2[53 - ColRightShift].R = r;
					array2[53 - ColRightShift].G = g;
					array2[53 - ColRightShift].B = b;
					break;
				case 14u:
					array2[52 - ColShift].R = r;
					array2[52 - ColShift].G = g;
					array2[52 - ColShift].B = b;
					break;
				}
				Set_ITE_Effect_Type_UserMode(m_ap_effect_data.save_light, 0, array2, bRefresh);
				Thread.Sleep(20 * m_ap_effect_data.save_speed);
				num++;
				if (num == num15 * 3)
				{
					num = 0u;
				}
				if (m_ap_effect_data.save_effect != 12)
				{
					num = 0u;
				}
			}
			bRefresh = false;
			if (m_effect_type != 4)
			{
				break;
			}
		}
		m_ap_effect_task = null;
	}

	private bool CheckCollsion(LEDActor lEDActor, List<LEDActor> correctLed)
	{
		foreach (LEDActor item in correctLed)
		{
			if (lEDActor != item && Actor.IsCollision(item, lEDActor))
			{
				item.DirectionReverse();
				return true;
			}
		}
		return false;
	}

	private RGB_S[] ConvertToLightBarMap(RGB_S[] _IntoColorList)
	{
		List<RGB_S> list = new List<RGB_S>();
		for (int i = 0; i < 40; i++)
		{
			list.Add(default(RGB_S));
		}
		List<int> list2 = new List<int>
		{
			35, 26, 17, 30, 21, 12, 25, 16, 7, 20,
			11, 2, 15, 6, 28, 5, 27, 18, 0, 22,
			13, 10, 1
		};
		for (int j = 0; j < list2.Count(); j++)
		{
			list[list2[j]] = _IntoColorList[j];
		}
		return list.ToArray();
	}

	public bool HID_Set_Effect_Type_08H(byte Control, byte Effect, byte Speed, byte Light, byte ColorIndex, byte Direction, byte Save)
	{
		if (Monitor.TryEnter(_08HLock, 1000))
		{
			try
			{
				_ = 4;
				byte[] buffer = new List<byte>
				{
					0,
					8,
					Control,
					Effect,
					Convert.ToByte(Speed),
					Light,
					ColorIndex,
					Direction,
					Save
				}.ToArray();
				m_HIDManager.WriteFeature(buffer);
				Thread.Sleep(1);
			}
			finally
			{
				Monitor.Exit(_08HLock);
			}
		}
		return true;
	}

	public bool HID_Set_Brightness_Level_09H(byte level)
	{
		_asyncSingleBrightness = level;
		byte b = 2;
		byte[] buffer = new byte[9] { 0, 9, b, level, 0, 0, 0, 0, 0 };
		m_HIDManager.WriteFeature(buffer);
		Thread.Sleep(1);
		return true;
	}

	private bool HID_Get_FirmwareVersion_80H(ref byte Ver_High, ref byte Ver_Low, ref byte Ver_Test, ref byte Ver_Customer)
	{
		if (Monitor.TryEnter(_08HLock, 1000))
		{
			try
			{
				int num = 0;
				while (num < 10)
				{
					byte[] buffer = new byte[9] { 0, 128, 0, 0, 0, 0, 0, 0, 0 };
					m_HIDManager.WriteFeature(buffer);
					Thread.Sleep(1);
					byte[] array = new byte[9];
					m_HIDManager.GetFeature(array);
					Thread.Sleep(1);
					Ver_High = array[2];
					Ver_Low = array[3];
					Ver_Test = array[4];
					Ver_Customer = array[5];
					if (array[1] != 128)
					{
						Log.s(LOG_LEVEL.ERROR, "Error count : " + num);
						num++;
						Thread.Sleep(20);
						continue;
					}
					return true;
				}
			}
			catch
			{
			}
			finally
			{
				Monitor.Exit(_08HLock);
			}
		}
		return true;
	}

	public bool HID_Set_TimeOut_1AH(byte enable, byte time, byte save)
	{
		if (Monitor.TryEnter(_08HLock, 1000))
		{
			try
			{
				byte[] buffer = new byte[9] { 0, 26, 0, enable, time, 0, 0, 0, save };
				m_HIDManager.WriteFeature(buffer);
				Thread.Sleep(1);
			}
			finally
			{
				Monitor.Exit(_08HLock);
			}
		}
		return true;
	}

	public bool HID_Get_Effect_Type_88H(ref byte Control, ref byte Effect, ref byte Speed, ref byte Light, ref byte ColorIndex, ref byte Direction)
	{
		byte[] buffer = new byte[9] { 0, 136, 0, 0, 0, 0, 0, 0, 0 };
		m_HIDManager.WriteFeature(buffer);
		Thread.Sleep(1);
		byte[] array = new byte[9];
		m_HIDManager.GetFeature(array);
		Thread.Sleep(1);
		Control = array[2];
		Effect = array[3];
		Speed = array[4];
		Light = array[5];
		ColorIndex = array[6];
		Direction = array[7];
		return true;
	}

	private bool HID_Set_Picture_12H(byte Saved)
	{
		byte[] buffer = new byte[9] { 0, 18, 0, 0, 8, 0, 0, 0, 0 };
		m_HIDManager.WriteFeature(buffer);
		Thread.Sleep(1);
		return true;
	}

	private bool HID_Set_Color_14H(byte Index, byte R, byte G, byte B)
	{
		byte[] buffer;
		if (m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_101 || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_102)
		{
			RGB_S rGB_S = WKDColor.cheatRGB_2ndME(R, G, B);
			buffer = new byte[9] { 0, 20, 0, Index, rGB_S.R, rGB_S.G, rGB_S.B, 0, 0 };
		}
		else if (MEZone_2p1ndSeries.Contains(m_ITE_KB_Type))
		{
			RGB_S rGB_S2 = WKDColor.cheatRGB_2p1ndME(R, G, B);
			buffer = new byte[9] { 0, 20, 0, Index, rGB_S2.R, rGB_S2.G, rGB_S2.B, 0, 0 };
		}
		else if (MEZone_2p2ndSeries.Contains(m_ITE_KB_Type))
		{
			RGB_S rGB_S3 = WKDColor.cheatRGB_2p2ndME(R, G, B);
			buffer = new byte[9] { 0, 20, 0, Index, rGB_S3.R, rGB_S3.G, rGB_S3.B, 0, 0 };
		}
		else if (m_ITE_KB_Type == RGBKB_Type.FourZone || m_ITE_KB_Type == RGBKB_Type.FourZoneSingleColor)
		{
			RGB_S rGB_S4 = WKDColor.cheatRGB_4Zone(m_Project_ID, R, G, B);
			buffer = new byte[9] { 0, 20, 0, Index, rGB_S4.R, rGB_S4.G, rGB_S4.B, 0, 0 };
		}
		else if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar)
		{
			RGB_S rGB_S5 = WKDColor.cheatRGB_HIDLightbar(R, G, B);
			buffer = new byte[9] { 0, 20, 0, Index, rGB_S5.R, rGB_S5.G, rGB_S5.B, 0, 0 };
		}
		else if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar2)
		{
			RGB_S rGB_S6 = WKDColor.cheatRGB_HIDLightbar2(R, G, B);
			buffer = new byte[9] { 0, 20, 0, Index, rGB_S6.R, rGB_S6.G, rGB_S6.B, 0, 0 };
		}
		else
		{
			buffer = new byte[9] { 0, 20, 0, Index, R, G, B, 0, 0 };
		}
		m_HIDManager.WriteFeature(buffer);
		Thread.Sleep(1);
		return true;
	}

	private bool HID_Set_RowIndex_16H(byte RowIndex)
	{
		byte[] buffer = new byte[9] { 0, 22, 0, RowIndex, 0, 0, 0, 0, 0 };
		m_HIDManager.WriteFeature(buffer);
		Thread.Sleep(1);
		return true;
	}

	private bool HID_Set_RowIndex_26H(byte RowIndex)
	{
		byte[] buffer = new byte[9] { 0, 38, 0, RowIndex, 0, 0, 0, 0, 0 };
		m_HIDManager.WriteFeature(buffer);
		return true;
	}

	private bool HID_Set_RowIndex_12H(byte RowIndex)
	{
		byte[] buffer = new byte[9] { 0, 18, 0, RowIndex, 0, 0, 0, 0, 0 };
		m_HIDManager.WriteFeature(buffer);
		Thread.Sleep(1);
		return true;
	}

	private void AudioData_WaveOutCenterHorizontalEventHandler(object sender)
	{
		try
		{
			RGB_S[] array = new RGB_S[126];
			byte audioLight = audioData.AudioLight;
			bool bRefresh = false;
			List<float> list = sender as List<float>;
			List<int> list2 = new List<int>();
			int num = 10 - ColShift;
			float value = EqualMachine(list, (byte)num) * list.Average();
			for (int i = 0; i < list.Count; i++)
			{
				list2.Add(Convert.ToInt32(value));
			}
			List<int> list3 = new List<int> { 9, 30, 51, 72, 93, 114 };
			for (int j = 0; j < list3.Count; j++)
			{
				list3[j] -= ColShift;
			}
			int num2 = 0;
			RGB_S[] array2 = null;
			if (audioData == null)
			{
				return;
			}
			if (audioData.ColorBuffer != null)
			{
				array2 = audioData.ColorBuffer;
			}
			for (int k = 0; k < list3.Count(); k++)
			{
				int num3 = ((list2[k] > num + 1) ? (num + 1) : list2[k]);
				int index = k;
				int num4 = list3[index];
				if (num3 > num2)
				{
					for (int l = 0; l < num3; l++)
					{
						int num5 = num4 + l;
						array[num5] = array2[0];
					}
				}
				if (num3 >= num2 + 2)
				{
					int num6 = num2 + 2;
					for (int m = num6; m < num3; m++)
					{
						array[num4 + m] = array2[num6 - 1];
					}
				}
				if (num3 >= num2 + 3)
				{
					int num7 = num2 + 3;
					for (int n = num7; n < num3; n++)
					{
						array[num4 + n] = array2[num7 - 1];
					}
				}
				if (num3 >= num2 + 4)
				{
					int num8 = num2 + 4;
					for (int num9 = num8; num9 < num3; num9++)
					{
						array[num4 + num9] = array2[num8 - 1];
					}
				}
				if (num3 >= num2 + 5)
				{
					int num10 = num2 + 5;
					for (int num11 = num10; num11 < num3; num11++)
					{
						array[num4 + num11] = array2[num10 - 1];
					}
				}
				if (num3 >= num2 + 6)
				{
					int num12 = num2 + 6;
					for (int num13 = num12; num13 < num3; num13++)
					{
						array[num4 + num13] = array2[num12 - 1];
					}
				}
				if (num3 >= num2 + 7)
				{
					int num14 = num2 + 7;
					for (int num15 = num14; num15 < num3; num15++)
					{
						int num16 = num4 + num15;
						array[num16] = array2[num14 - 1];
					}
				}
			}
			List<int> list4 = new List<int> { 9, 30, 51, 72, 93, 114 };
			for (int num17 = 0; num17 < list4.Count; num17++)
			{
				list4[num17] -= ColShift;
			}
			int num18 = list2.Count() / 2;
			for (int num19 = num18; num19 < list4.Count + num18; num19++)
			{
				int num20 = ((list2[num19] > num) ? num : list2[num19]);
				int index2 = num19 - num18;
				int num21 = list4.OrderByDescending((int result) => result).ToList()[index2];
				if (num20 > num2)
				{
					for (int num22 = 0; num22 < num20; num22++)
					{
						int num23 = num21 - num22;
						array[num23] = array2[0];
					}
				}
				if (num20 >= num2 + 2)
				{
					int num24 = num2 + 2;
					for (int num25 = num24; num25 < num20; num25++)
					{
						array[num21 - num25] = array2[num24 - 1];
					}
				}
				if (num20 >= num2 + 3)
				{
					int num26 = num2 + 3;
					for (int num27 = num26; num27 < num20; num27++)
					{
						array[num21 - num27] = array2[num26 - 1];
					}
				}
				if (num20 >= num2 + 4)
				{
					int num28 = num2 + 4;
					for (int num29 = num28; num29 < num20; num29++)
					{
						array[num21 - num29] = array2[num28 - 1];
					}
				}
				if (num20 >= num2 + 5)
				{
					int num30 = num2 + 5;
					for (int num31 = num30; num31 < num20; num31++)
					{
						array[num21 - num31] = array2[num30 - 1];
					}
				}
				if (num20 >= num2 + 6)
				{
					int num32 = num2 + 6;
					for (int num33 = num32; num33 < num20; num33++)
					{
						array[num21 - num33] = array2[num32 - 1];
					}
				}
				if (num20 >= num2 + 7)
				{
					int num34 = num2 + 7;
					for (int num35 = num34; num35 < num20; num35++)
					{
						int num36 = num21 - num35;
						array[num36] = array2[num34 - 1];
					}
				}
			}
			Set_ITE_Effect_Type_UserMode_Dynamic(audioLight, 0, array, bRefresh);
		}
		catch (Exception ex)
		{
			Log.s(LOG_LEVEL.ERROR, $"MusicMode failed,Horizon Function ={ex.ToString()}  ");
		}
	}

	private void AudioData_WaveOutHorizontalEventHandler(object sender)
	{
		try
		{
			RGB_S[] array = new RGB_S[126];
			byte audioLight = audioData.AudioLight;
			bool bRefresh = false;
			List<float> list = sender as List<float>;
			List<int> list2 = new List<int>();
			int num = 10 - ColShift;
			float value = EqualMachine(list, (byte)num) * list.Average();
			for (int i = 0; i < list.Count; i++)
			{
				list2.Add(Convert.ToInt32(value));
			}
			_ = new
			{
				R = 255,
				G = 0,
				B = 0
			};
			_ = new
			{
				R = 100,
				G = 200,
				B = 0
			};
			_ = new
			{
				R = 0,
				G = 255,
				B = 0
			};
			List<int> list3 = new List<int> { 105, 84, 63, 42, 21, 0 };
			int num2 = 0;
			RGB_S[] array2 = null;
			if (audioData == null)
			{
				return;
			}
			if (audioData.ColorBuffer != null)
			{
				array2 = audioData.ColorBuffer;
			}
			for (int j = 0; j < list3.Count; j++)
			{
				int num3 = ((list2[j] > num) ? num : list2[j]);
				int index = j;
				int num4 = list3[index];
				if (num3 > num2)
				{
					for (int k = 0; k < num3; k++)
					{
						array[num4 + k] = array2[0];
					}
				}
				if (num3 >= num2 + 2)
				{
					int num5 = num2 + 2;
					for (int l = num5; l < num3; l++)
					{
						array[num4 + l] = array2[num5 - 1];
					}
				}
				if (num3 >= num2 + 3)
				{
					int num6 = num2 + 3;
					for (int m = num6; m < num3; m++)
					{
						array[num4 + m] = array2[num6 - 1];
					}
				}
				if (num3 >= num2 + 4)
				{
					int num7 = num2 + 4;
					for (int n = num7; n < num3; n++)
					{
						array[num4 + n] = array2[num7 - 1];
					}
				}
				if (num3 >= num2 + 5)
				{
					int num8 = num2 + 5;
					for (int num9 = num8; num9 < num3; num9++)
					{
						array[num4 + num9] = array2[num8 - 1];
					}
				}
				if (num3 >= num2 + 6)
				{
					int num10 = num2 + 6;
					for (int num11 = num10; num11 < num3; num11++)
					{
						array[num4 + num11] = array2[num10 - 1];
					}
				}
				if (num3 >= num2 + 7)
				{
					int num12 = num2 + 7;
					for (int num13 = num12; num13 < num3; num13++)
					{
						array[num4 + num13] = array2[num12 - 1];
					}
				}
			}
			List<int> list4 = new List<int> { 18, 39, 60, 81, 102, 123 };
			for (int num14 = 0; num14 < list4.Count; num14++)
			{
				list4[num14] -= ColRightShift;
			}
			int num15 = list2.Count() / 2;
			for (int num16 = num15; num16 < list4.Count + num15; num16++)
			{
				int num17 = ((list2[num16] > num) ? num : list2[num16]);
				int num18 = num16;
				int num19 = list4.OrderByDescending((int result) => result).ToList()[num18 - list2.Count() / 2];
				if (num17 > num2)
				{
					for (int num20 = 0; num20 < num17; num20++)
					{
						array[num19 - num20] = array2[0];
					}
				}
				if (num17 >= num2 + 2)
				{
					int num21 = num2 + 2;
					for (int num22 = num21; num22 < num17; num22++)
					{
						array[num19 - num22] = array2[num21 - 1];
					}
				}
				if (num17 >= num2 + 3)
				{
					int num23 = num2 + 3;
					for (int num24 = num23; num24 < num17; num24++)
					{
						array[num19 - num24] = array2[num23 - 1];
					}
				}
				if (num17 >= num2 + 4)
				{
					int num25 = num2 + 4;
					for (int num26 = num25; num26 < num17; num26++)
					{
						array[num19 - num26] = array2[num25 - 1];
					}
				}
				if (num17 >= num2 + 5)
				{
					int num27 = num2 + 5;
					for (int num28 = num27; num28 < num17; num28++)
					{
						array[num19 - num28] = array2[num27 - 1];
					}
				}
				if (num17 >= num2 + 6)
				{
					int num29 = num2 + 6;
					for (int num30 = num29; num30 < num17; num30++)
					{
						array[num19 - num30] = array2[num29 - 1];
					}
				}
				if (num17 >= num2 + 7)
				{
					int num31 = num2 + 7;
					for (int num32 = num31; num32 < num17; num32++)
					{
						array[num19 - num32] = array2[num31 - 1];
					}
				}
			}
			Set_ITE_Effect_Type_UserMode_Dynamic(audioLight, 0, array, bRefresh);
		}
		catch (Exception ex)
		{
			Log.s(LOG_LEVEL.ERROR, $"MusicMode failed,Horizon Function ={ex.ToString()}  ");
		}
	}

	private void AudioData_WaveOutEventHandler(object sender)
	{
		try
		{
			RGB_S[] array = new RGB_S[126];
			byte audioLight = audioData.AudioLight;
			bool bRefresh = false;
			List<float> list = sender as List<float>;
			List<int> list2 = new List<int>();
			for (int i = ColShift; i < list.Count; i++)
			{
				list2.Add(Convert.ToInt32(list[i]));
			}
			int num = 126;
			int num2 = 105;
			int num3 = 84;
			int num4 = 63;
			int num5 = 42;
			int num6 = 21;
			int num7 = 0;
			int num8 = 0;
			RGB_S[] array2 = null;
			if (audioData == null)
			{
				return;
			}
			if (audioData.ColorBuffer != null)
			{
				array2 = audioData.ColorBuffer;
			}
			for (int j = 0; j < list2.Count(); j++)
			{
				int num9 = list2[j];
				if (num2 + j < num && num9 > num8)
				{
					array[num2 + j] = array2[0];
				}
				if (num3 + j < num2 - 1 && num9 > num8 + 1)
				{
					array[num3 + j] = array2[1];
				}
				if (num4 + j < num3 - 1 && num9 > num8 + 2)
				{
					array[num4 + j] = array2[2];
				}
				if (num5 + j < num4 - 1 && num9 > num8 + 3)
				{
					array[num5 + j] = array2[3];
				}
				if (num6 + j < num5 - 1 && num9 > num8 + 4)
				{
					array[num6 + j] = array2[4];
				}
				if (num7 + j < num6 - 1 && num9 > num8 + 5)
				{
					array[num7 + j] = array2[5];
				}
			}
			Set_ITE_Effect_Type_UserMode_Dynamic(audioLight, 0, array, bRefresh);
		}
		catch (Exception ex)
		{
			Log.s(LOG_LEVEL.ERROR, $"MusicMode failed,Vertical Function ={ex.ToString()}  ");
		}
	}

	private float AdjustMeterParam(byte speed)
	{
		return speed switch
		{
			10 => 0.5f, 
			7 => 1.5f, 
			5 => 2.5f, 
			3 => 3.5f, 
			1 => 4.5f, 
			_ => 0.5f, 
		};
	}

	private bool DLL_SetMusicMode(bool enable, byte light_level = 4, byte speed = 1, byte direction = 0, RGB_S[] colorBuffer = null)
	{
		try
		{
			if (enable)
			{
				audioData = AudioData.Instance;
				if (audioData == null)
				{
					return false;
				}
				audioData.EveryDelayTime = 0.3f;
				if (MEZone_2p1ndSeries.Contains(m_ITE_KB_Type))
				{
					audioData.DelayTime = 30;
					audioData.TimeOut = 40;
				}
				else
				{
					audioData.DelayTime = 10;
					audioData.TimeOut = 20;
				}
				float value = AdjustMeterParam(speed);
				audioData.Speed = Convert.ToSingle(value);
				audioData.AudioLight = light_level;
				if (colorBuffer != null)
				{
					audioData.ColorBuffer = colorBuffer;
				}
				if (MEZone_2p1ndSeries.Contains(m_ITE_KB_Type) || MEZone_2p2ndSeries.Contains(m_ITE_KB_Type) || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_101 || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_102)
				{
					LogCtrl.Write("SetMusicKeyboardSwitch " + enable);
					audioData.SetKeyboardSwitch(enable: true, audioData.ColorBuffer);
					HID_Set_Effect_Type_08H(2, 34, 0, light_level, 0, 0, 0);
					Set_ITE_Effect_Type_UserMode_Dynamic(light_level, 0, new RGB_S[126], bRefresh: true);
				}
				else if (MEZone_LightbarSeries.Contains(m_ITE_KB_Type))
				{
					LogCtrl.Write("SetMusicLightbarSwitch " + enable);
					audioData.SetLightbarSwitch(enable: true, audioData.ColorBuffer);
					HID_Set_Effect_Type_08H(2, 34, 0, light_level, 0, 0, 0);
					if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar)
					{
						Set_ITE_Effect_Type_UserMode_Lightbar12h(light_level, 0, new RGB_S[126], bRefresh: true);
					}
					else if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar2)
					{
						Set_ITE_Effect_Type_UserMode_Lightbar2(light_level, 0, new RGB_S[40], bRefresh: true, 3);
					}
				}
				else if (m_ITE_KB_Type == RGBKB_Type.FourZone || m_ITE_KB_Type == RGBKB_Type.FourZoneSingleColor)
				{
					LogCtrl.Write("SetMusicKeyboardSwitch " + enable);
					audioData.SetKeyboardSwitch(enable: true, audioData.ColorBuffer);
				}
				switch (direction)
				{
				case 1:
					audioData.MusicType = MUSICTYPE.LEFTRIGHTSTEREO;
					audioData.ColumNumbers = 12;
					break;
				case 2:
					audioData.MusicType = MUSICTYPE.CENTERLEFTRIGHTSTEREO;
					audioData.ColumNumbers = 12;
					break;
				case 3:
					audioData.MusicType = MUSICTYPE.STEREO;
					audioData.ColumNumbers = 19;
					break;
				default:
					if (audioData == null)
					{
						break;
					}
					audioData.MusicType = MUSICTYPE.NORMAL;
					if (m_ITE_KB_Type == RGBKB_Type.FourZone || m_ITE_KB_Type == RGBKB_Type.FourZoneSingleColor)
					{
						RGBKB_Color layout_color = new RGBKB_Color
						{
							ColorBlocks = 4u,
							isCircular = true
						};
						for (int i = 0; i < colorBuffer.Count(); i++)
						{
							colorBuffer[i] = colorBuffer[i];
						}
						layout_color.ColorBuffer = colorBuffer;
						if (colorBuffer != null)
						{
							SetSingleEffect(1, 0, 0, 0, 0, layout_color);
						}
						audioData.MusicType = MUSICTYPE.BRIGHTNESS;
					}
					else if (MEZone_LightbarSeries.Contains(m_ITE_KB_Type))
					{
						RGBKB_Color rGBKB_Color = new RGBKB_Color
						{
							ColorBuffer = colorBuffer
						};
						audioData.MusicType = MUSICTYPE.BRIGHTNESS;
					}
					audioData.ColumNumbers = 19;
					break;
				}
				if (audioData != null)
				{
					if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar)
					{
						audioData.LightbarEventHandler -= AudioData_LightbarEventHandler;
						audioData.LightbarEventHandler += AudioData_LightbarEventHandler;
					}
					else if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar2)
					{
						audioData.LightbarEventHandler -= AudioData_Lightbar2EventHandler;
						audioData.LightbarEventHandler += AudioData_Lightbar2EventHandler;
					}
					if (!MEZone_LightbarSeries.Contains(m_ITE_KB_Type))
					{
						audioData.KeyBoardWaveLeftRightOutEventHandler -= AudioData_WaveOutHorizontalEventHandler;
						audioData.KeyBoardWaveOutEventHandler -= AudioData_WaveOutEventHandler;
						audioData.KeyBoardWaveCenterLeftRightOutEventHandler -= AudioData_WaveOutCenterHorizontalEventHandler;
						audioData.KeyBoardWaveBrightnessEventHandler -= AudioData_KeybaoradWaveBrightnewssEventHandlerForAll;
						audioData.KeyBoardWaveLeftRightOutEventHandler += AudioData_WaveOutHorizontalEventHandler;
						audioData.KeyBoardWaveOutEventHandler += AudioData_WaveOutEventHandler;
						audioData.KeyBoardWaveCenterLeftRightOutEventHandler += AudioData_WaveOutCenterHorizontalEventHandler;
						audioData.KeyBoardWaveBrightnessEventHandler += AudioData_KeybaoradWaveBrightnewssEventHandlerForAll;
					}
					audioData.WaveOutAudioStart();
				}
			}
			else
			{
				if (MEZone_LightbarSeries.Contains(m_ITE_KB_Type))
				{
					audioData?.SetLightbarSwitch(enable: false, null);
				}
				else if (MEZone_2p1ndSeries.Contains(m_ITE_KB_Type) || MEZone_2p2ndSeries.Contains(m_ITE_KB_Type) || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_101 || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_102 || m_ITE_KB_Type == RGBKB_Type.FourZone || m_ITE_KB_Type == RGBKB_Type.FourZoneSingleColor)
				{
					audioData?.SetKeyboardSwitch(enable: false, null);
				}
				if (audioData != null)
				{
					audioData.WaveOutAudioStop();
				}
				if (audioData != null && !audioData.GetKeyboardSwitch() && !audioData.GetLighbarSwitch())
				{
					audioData = null;
				}
				Thread.Sleep(50);
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Music Mode " + ex.ToString());
		}
		return true;
	}

	private void AudioData_Lightbar2EventHandler(object sender)
	{
		try
		{
			VerticalColorList = new List<List<RGB_S>>();
			RGB_S[] array = new RGB_S[40];
			byte audioLight = audioData.AudioLight;
			bool bRefresh = false;
			List<float> list = sender as List<float>;
			List<int> list2 = new List<int>();
			int num = 35;
			float num2 = EqualMachine(list, (byte)num) * list.Average();
			for (int i = 0; i < list.Count; i++)
			{
				list2.Add(Convert.ToInt32(num2));
			}
			RGB_S[] array2 = null;
			if (audioData == null || audioData.GetLightbarColor() == null)
			{
				return;
			}
			array2 = audioData.GetLightbarColor();
			for (int j = 0; j < 5; j++)
			{
				VerticalColorList.Add(new List<RGB_S>());
			}
			int num3 = 1;
			RGB_S[] array3 = array2;
			foreach (RGB_S item in array3)
			{
				VerticalColorList[0].Add(item);
				num3++;
			}
			for (int l = 1; l < 5; l++)
			{
				for (int m = 0; m < array2.Length; m++)
				{
					double value = VerticalColorList[0][m].R * (5 - l) / 5;
					double value2 = VerticalColorList[0][m].G * (5 - l) / 5;
					double value3 = VerticalColorList[0][m].B * (5 - l) / 5;
					VerticalColorList[l].Add(new RGB_S((uint)l, Convert.ToByte(value), Convert.ToByte(value2), Convert.ToByte(value3)));
				}
			}
			if (!(num2 < (float)num))
			{
				return;
			}
			try
			{
				int num4 = Convert.ToInt32(num2) / 7;
				int num5 = Convert.ToInt32(num2) % 7;
				if (num4 >= 5)
				{
					num4 = 4;
				}
				for (int n = 0; n <= num5; n++)
				{
					array[6 - n] = VerticalColorList[4 - num4][n];
				}
				if (num5 == 0 && num4 == 0)
				{
					for (int num6 = 0; num6 < 40; num6++)
					{
						array[num6] = new RGB_S
						{
							R = 0,
							G = 0,
							B = 0
						};
					}
				}
				Set_ITE_Effect_Type_UserMode_Lightbar2(audioLight, 0, array, bRefresh, 3);
			}
			catch (Exception)
			{
			}
		}
		catch (Exception ex2)
		{
			Log.s(LOG_LEVEL.ERROR, $"MusicMode failed,Horizon Function ={ex2.ToString()}  ");
		}
	}

	private void AudioData_LightbarEventHandler(object sender)
	{
		try
		{
			RGB_S[] array = new RGB_S[40];
			byte audioLight = audioData.AudioLight;
			bool bRefresh = false;
			List<float> list = sender as List<float>;
			List<int> list2 = new List<int>();
			int num = 12;
			float value = EqualMachine(list, (byte)num) * list.Average();
			for (int i = 0; i < list.Count; i++)
			{
				list2.Add(Convert.ToInt32(value));
			}
			int num2 = 0;
			RGB_S[] array2 = null;
			if (audioData.GetLightbarColor() != null)
			{
				array2 = audioData.GetLightbarColor();
			}
			int num3 = ((list2[0] > num + 1) ? (num + 1) : list2[0]);
			int num4 = 11;
			if (num3 > num2)
			{
				for (int j = 0; j < num3; j++)
				{
					int num5 = num4 + j;
					array[num5] = array2[0];
				}
			}
			if (num3 >= num2 + 2)
			{
				int num6 = num2 + 2;
				for (int k = num6; k < num3; k++)
				{
					array[num4 + k] = array2[num6 - 1];
				}
			}
			if (num3 >= num2 + 3)
			{
				int num7 = num2 + 3;
				for (int l = num7; l < num3; l++)
				{
					array[num4 + l] = array2[num7 - 1];
				}
			}
			if (num3 >= num2 + 4)
			{
				int num8 = num2 + 4;
				for (int m = num8; m < num3; m++)
				{
					array[num4 + m] = array2[num8 - 1];
				}
			}
			if (num3 >= num2 + 5)
			{
				int num9 = num2 + 5;
				for (int n = num9; n < num3; n++)
				{
					array[num4 + n] = array2[num9 - 1];
				}
			}
			if (num3 >= num2 + 6)
			{
				int num10 = num2 + 6;
				for (int num11 = num10; num11 < num3; num11++)
				{
					array[num4 + num11] = array2[num10 - 1];
				}
			}
			if (num3 >= num2 + 7)
			{
				int num12 = num2 + 7;
				for (int num13 = num12; num13 < num3; num13++)
				{
					int num14 = num4 + num13;
					array[num14] = array2[num12 - 1];
				}
			}
			num3 = ((list2[0] > num) ? num : list2[0]);
			num4 = 11;
			if (num3 > num2)
			{
				for (int num15 = 0; num15 < num3; num15++)
				{
					int num16 = num4 - num15;
					array[num16] = array2[0];
				}
			}
			if (num3 >= num2 + 2)
			{
				int num17 = num2 + 2;
				for (int num18 = num17; num18 < num3; num18++)
				{
					array[num4 - num18] = array2[num17 - 1];
				}
			}
			if (num3 >= num2 + 3)
			{
				int num19 = num2 + 3;
				for (int num20 = num19; num20 < num3; num20++)
				{
					array[num4 - num20] = array2[num19 - 1];
				}
			}
			if (num3 >= num2 + 4)
			{
				int num21 = num2 + 4;
				for (int num22 = num21; num22 < num3; num22++)
				{
					array[num4 - num22] = array2[num21 - 1];
				}
			}
			if (num3 >= num2 + 5)
			{
				int num23 = num2 + 5;
				for (int num24 = num23; num24 < num3; num24++)
				{
					array[num4 - num24] = array2[num23 - 1];
				}
			}
			if (num3 >= num2 + 6)
			{
				int num25 = num2 + 6;
				for (int num26 = num25; num26 < num3; num26++)
				{
					array[num4 - num26] = array2[num25 - 1];
				}
			}
			if (num3 >= num2 + 7)
			{
				int num27 = num2 + 7;
				for (int num28 = num27; num28 < num3; num28++)
				{
					int num29 = num4 - num28;
					array[num29] = array2[num27 - 1];
				}
			}
			Set_ITE_Effect_Type_UserMode_Lightbar12h(audioLight, 0, array, bRefresh);
		}
		catch (Exception ex)
		{
			Log.s(LOG_LEVEL.ERROR, $"MusicMode failed,Horizon Function ={ex.ToString()}  ");
		}
	}

	public void ResetEqualMachine()
	{
		EqualsMachMax = 0f;
		EqualsMachMin = float.MaxValue;
	}

	private float EqualMachine(List<float> meterValue, byte target)
	{
		if (target == 0)
		{
			return 0f;
		}
		if (meterValue.Average() > EqualsMachMax)
		{
			EqualsMachMax = meterValue.Average();
		}
		if (meterValue.Min() < EqualsMachMin)
		{
			EqualsMachMin = meterValue.Min();
		}
		if (meterValue.All((float n) => n.Equals(0f)))
		{
			EqualsMachMax = 0f;
			EqualsMachMin = float.MaxValue;
		}
		float result = (float)(int)target / (EqualsMachMax - EqualsMachMin);
		if (EqualsMachMax - EqualsMachMin == 0f)
		{
			return 0f;
		}
		return result;
	}

	private void AudioData_KeybaoradWaveBrightnewssEventHandlerForAll(object sender)
	{
		if (audioData != null)
		{
			_ = audioData.AudioLight;
		}
		List<float> list = sender as List<float>;
		if (list.Count > 0)
		{
			float num = EqualMachine(list, 50);
			float num2 = list.Average() * num;
			if (float.IsInfinity(num2) || float.IsNaN(num2))
			{
				HID_Set_Brightness_Level_09H((byte)Convert.ToInt32(0));
			}
			else
			{
				HID_Set_Brightness_Level_09H((byte)Convert.ToInt32(num2));
			}
		}
	}

	private void AudioData_KeyBoardWaveBrightnessEventHandler(object sender)
	{
		try
		{
			RGB_S[] array = new RGB_S[126];
			byte audioLight = audioData.AudioLight;
			List<float> list = new List<float>();
			for (float num = 0f; num <= 1f; num += 0.1f)
			{
				list.Add(num);
			}
			list[0] = 0.1f;
			bool bRefresh = false;
			List<float> source = sender as List<float>;
			_ = ColShift;
			RGB_S[] array2 = null;
			if (audioData.ColorBuffer != null)
			{
				array2 = audioData.ColorBuffer;
			}
			int num2 = Convert.ToInt32(source.Max());
			Convert.ToInt32(source.Min());
			num2 = ((num2 > 10) ? 10 : num2);
			sw.Start();
			for (int i = 0; i < array2.Length; i++)
			{
				int num3 = num2 - i % AnimationShift;
				num3 = ((num3 >= 0) ? num3 : 0);
				num3 = ((num3 > 10) ? 10 : num3);
				array[i].R = Convert.ToByte((float)(int)array2[i].R * list[num3]);
				array[i].G = Convert.ToByte((float)(int)array2[i].G * list[num3]);
				array[i].B = Convert.ToByte((float)(int)array2[i].B * list[num3]);
				if (sw.ElapsedMilliseconds >= 10000)
				{
					sw.Reset();
					AnimationShift += shiftvalue;
					shiftCount++;
					if (shiftCount == 3)
					{
						shiftCount = 0;
						shiftvalue = -1 * shiftvalue;
					}
				}
			}
			Set_ITE_Effect_Type_UserMode_Dynamic(audioLight, 0, array, bRefresh);
		}
		catch (Exception ex)
		{
			Log.s(LOG_LEVEL.ERROR, $"Usermode Music Function ={ex.ToString()}  ");
		}
	}

	private bool Disable_EC_OnkeyPressed()
	{
		if (m_enableOnkeyPressed)
		{
			m_enableOnkeyPressed = false;
		}
		return true;
	}

	private bool Enable_EC_OnkeyPressed(byte effect, byte direction)
	{
		if (m_enableOnkeyPressed)
		{
			return true;
		}
		if ((effect == 6 || effect == 14 || effect == 17 || effect == 4) && direction == 1)
		{
			byte Data = 0;
			EcCtrl.Read(GetType().Name, 1857, ref Data);
			byte b = (byte)Convert.ToUInt64(Data);
			b |= 8;
			EcCtrl.Write(GetType().Name, 1857, b);
			m_enableOnkeyPressed = true;
		}
		return true;
	}

	public static void log(string strLog)
	{
		string path = "C:\\temp\\musicTime.txt";
		if (File.Exists(path))
		{
			File.AppendAllText(path, strLog + "\n", Encoding.Default);
		}
		else
		{
			File.Create(path);
		}
	}

	private RGB_S BackgroundColorConverter(int colorindex)
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
			result.R = 11;
			result.G = 2;
			break;
		case 4:
			result.G = 1;
			break;
		case 5:
			result.B = 1;
			break;
		case 6:
			result.G = 1;
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

	private RGB_S APBackgroundColorConverter(int colorindex)
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
			result.G = 2;
			break;
		case 3:
			result.R = 8;
			result.G = 4;
			break;
		case 4:
			result.G = 2;
			break;
		case 5:
			result.G = 2;
			result.B = 2;
			break;
		case 6:
			result.B = 2;
			break;
		case 7:
			result.R = 4;
			result.B = 3;
			break;
		case 8:
			result.R = 2;
			result.G = 2;
			result.B = 2;
			break;
		}
		return result;
	}

	private void Set_ITE_Effect_Type_UserModeBy12H(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh)
	{
		Log.s(LOG_LEVEL.TRACE, $"RGBKeyboard_ITE | Set_ITE_Effect_Type_StaticMode light ={Light}");
		lock (lock_12h_test)
		{
			if (bRefresh)
			{
				Light_Lock();
				HID_Set_Effect_Type_08H(2, 51, 0, Light, 0, 0, Save);
			}
			List<RGB_S> list = ColorBufferConvertTo12H(colorBuffer);
			List<byte[]> list2 = new List<byte[]>();
			int num = 0;
			for (int i = 0; i < 8; i++)
			{
				byte[] array = new byte[65];
				for (byte b = 1; b < 65; b += 4)
				{
					RGB_S rGB_S = default(RGB_S);
					if (num < list.Count)
					{
						rGB_S = list[num];
					}
					RGB_S rGB_S2 = ((!MEZone_2p2ndSeries.Contains(m_ITE_KB_Type)) ? WKDColor.cheatRGB_2ndME(rGB_S.R, rGB_S.G, rGB_S.B) : WKDColor.cheatRGB_2p2ndME(rGB_S.R, rGB_S.G, rGB_S.B));
					array[b] = 0;
					array[b + 1] = rGB_S2.R;
					array[b + 2] = rGB_S2.G;
					array[b + 3] = rGB_S2.B;
					num++;
				}
				list2.Add(array);
			}
			Light_Lock();
			HID_Set_Picture_12H(0);
			foreach (byte[] item in list2)
			{
				if (!Monitor.TryEnter(usbTransferLock, 5))
				{
					continue;
				}
				try
				{
					m_HIDDevice.Write(item.ToArray(), 0, item.ToArray().Length);
				}
				catch (Exception)
				{
				}
				finally
				{
					Monitor.Exit(usbTransferLock);
				}
			}
		}
	}

	private List<RGB_S> ColorBufferConvertTo12H(RGB_S[] colorBuffer)
	{
		List<List<RGB_S>> list = new List<List<RGB_S>>();
		for (int i = 0; i < 6; i++)
		{
			List<RGB_S> list2 = new List<RGB_S>();
			for (int j = 0; j < 21; j++)
			{
				int num = 5 - i;
				int num2 = j + num * 21;
				list2.Add(colorBuffer[num2]);
			}
			list.Add(list2);
		}
		List<RGB_S> list3 = new List<RGB_S>();
		for (int k = 0; k < list[0].Count; k++)
		{
			for (int l = 0; l < list.Count; l++)
			{
				list3.Add(list[l][k]);
			}
		}
		return list3;
	}

	private bool Set_ITE_Effect_Type_UserMode_Lightbar(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh)
	{
		Thread.Sleep(3);
		colorBuffer = ConvertToLightBarMap(colorBuffer);
		RGB_S rGB_S = APBackgroundColorConverter(NightModeSelectColorIndex);
		if (NightMode == 4 && Convert.ToUInt32(Light) <= 50)
		{
			Light = Convert.ToByte(50);
		}
		if (bRefresh)
		{
			Light_Lock();
			HID_Set_Effect_Type_08H(2, 51, 0, Light, 0, 0, Save);
		}
		byte[] array = new byte[65];
		array[0] = 0;
		array[1] = 0;
		for (byte b = 0; b < 8; b++)
		{
			for (byte b2 = 0; b2 < 5; b2++)
			{
				int num = 7 - b;
				int num2 = b2 + num * 5;
				if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar)
				{
					RGB_S rGB_S2 = WKDColor.cheatRGB_HIDLightbar(colorBuffer[num2].R, colorBuffer[num2].G, colorBuffer[num2].B);
					if (NightMode == 4)
					{
						double num3 = Convert.ToDouble(UserModeLight) / 50.0;
						array[2 + b2] = (byte)((rGB_S2.B == 0) ? ((double)(rGB_S2.B + rGB_S.B)) : ((double)(int)rGB_S2.B * num3));
						array[23 + b2] = (byte)((rGB_S2.G == 0) ? ((double)(rGB_S2.G + rGB_S.G)) : ((double)(int)rGB_S2.G * num3));
						array[44 + b2] = (byte)((rGB_S2.R == 0) ? ((double)(rGB_S2.R + rGB_S.R)) : ((double)(int)rGB_S2.R * num3));
					}
					else
					{
						array[2 + b2] = rGB_S2.B;
						array[23 + b2] = rGB_S2.G;
						array[44 + b2] = rGB_S2.R;
					}
				}
				else
				{
					array[2 + b2] = colorBuffer[num2].B;
					array[23 + b2] = colorBuffer[num2].G;
					array[44 + b2] = colorBuffer[num2].R;
				}
			}
			if (b == 0)
			{
				for (int i = 0; i < 5; i++)
				{
					if (i == 1)
					{
						array[2 + i] = colorBuffer[7].B;
						array[23 + i] = colorBuffer[7].G;
						array[44 + i] = colorBuffer[7].R;
					}
					if (i == 2)
					{
						array[2 + i] = colorBuffer[6].B;
						array[23 + i] = colorBuffer[6].G;
						array[44 + i] = colorBuffer[6].R;
					}
					if (i == 3)
					{
						array[2 + i] = colorBuffer[5].B;
						array[23 + i] = colorBuffer[5].G;
						array[44 + i] = colorBuffer[5].R;
					}
				}
			}
			try
			{
				Light_Lock();
				HID_Set_RowIndex_16H(b);
				Light_Lock();
				m_HIDDevice.Write(array, 0, array.Length);
				Thread.Sleep(1);
			}
			catch (Exception)
			{
			}
		}
		return true;
	}

	private bool Set_ITE_Effect_Type_UserMode_Lightbar12h(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh)
	{
		if (!LBuserModeLock)
		{
			return true;
		}
		LBuserModeLock = false;
		APBackgroundColorConverter(NightModeSelectColorIndex);
		if (NightMode == 4 && Convert.ToUInt32(Light) <= 50)
		{
			Light = Convert.ToByte(50);
		}
		if (bRefresh)
		{
			Light_Lock();
			HID_Set_Effect_Type_08H(2, 51, 0, Light, 0, 0, Save);
		}
		for (byte b = 0; b < 2; b++)
		{
			byte[] array = new byte[65];
			array[0] = 0;
			array[1] = 0;
			for (byte b2 = 0; b2 < 21; b2++)
			{
				int num = b2 + b * 21;
				int num2 = b2 * 3;
				if (num < colorBuffer.Length)
				{
					RGB_S rGB_S = WKDColor.cheatRGB_HIDLightbar(colorBuffer[num].R, colorBuffer[num].G, colorBuffer[num].B);
					array[2 + num2] = rGB_S.B;
					array[3 + num2] = rGB_S.G;
					array[4 + num2] = rGB_S.R;
				}
			}
			try
			{
				Light_Lock();
				HID_Set_RowIndex_12H(Convert.ToByte(b));
				Light_Lock();
				if (m_HIDDevice != null)
				{
					m_HIDDevice.Write(array, 0, array.Length);
				}
			}
			catch (Exception)
			{
				LBuserModeLock = true;
			}
			Thread.Sleep(1);
		}
		LBuserModeLock = true;
		return true;
	}

	private bool Set_ITE_Effect_Type_UserMode_Lightbar2(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh, int StartIndex)
	{
		if (!LBuserModeLock)
		{
			return true;
		}
		LBuserModeLock = false;
		APBackgroundColorConverter(NightModeSelectColorIndex);
		if (NightMode == 4 && Convert.ToUInt32(Light) <= 50)
		{
			Light = Convert.ToByte(50);
		}
		if (bRefresh)
		{
			Light_Lock();
			HID_Set_Effect_Type_08H(2, 51, 0, Light, 0, 0, Save);
		}
		for (byte b = 0; b < 1; b++)
		{
			byte[] array = new byte[65];
			array[0] = 0;
			array[1] = 0;
			for (byte b2 = 0; b2 < 21; b2++)
			{
				int num = b2 + b * 21;
				int num2 = b2 * 3;
				RGB_S rGB_S = WKDColor.cheatRGB_HIDLightbar2(colorBuffer[num].R, colorBuffer[num].G, colorBuffer[num].B);
				array[2 + num2] = rGB_S.B;
				array[3 + num2] = rGB_S.G;
				array[4 + num2] = rGB_S.R;
			}
			try
			{
				Light_Lock();
				HID_Set_RowIndex_12H(Convert.ToByte(StartIndex));
				Light_Lock();
				if (m_HIDDevice != null)
				{
					m_HIDDevice.Write(array, 0, array.Length);
				}
			}
			catch (Exception)
			{
				LBuserModeLock = true;
			}
			Thread.Sleep(1);
		}
		LBuserModeLock = true;
		return true;
	}

	public static bool compareArr(byte[] arr1, byte[] arr2)
	{
		if (arr1.Count() == arr2.Count())
		{
			for (int i = 0; i < arr1.Count(); i++)
			{
				if (arr1[i] != arr2[i])
				{
					return false;
				}
			}
			return true;
		}
		return false;
	}

	private bool CheckKBBufferPlan(int row, byte[] buffer)
	{
		bool num = compareArr(perKBBuffer[row], buffer);
		perKBBuffer[row] = buffer;
		if (num)
		{
			return false;
		}
		return true;
	}

	private bool CheckLBBufferPlan(int row, byte[] buffer)
	{
		bool num = compareArr(perLBBuffer[row], buffer);
		perLBBuffer[row] = buffer;
		if (num)
		{
			return false;
		}
		return true;
	}

	private bool Set_ITE_Effect_Type_UserMode(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh)
	{
		sw.Restart();
		if (!KBuserModeLock)
		{
			return true;
		}
		KBuserModeLock = false;
		RGB_S rGB_S = APBackgroundColorConverter(NightModeSelectColorIndex);
		if (NightMode == 4 && Convert.ToUInt32(Light) <= 50)
		{
			Light = Convert.ToByte(50);
		}
		if (bRefresh)
		{
			Light_Lock();
			HID_Set_Effect_Type_08H(2, 51, 0, Light, 0, 0, Save);
		}
		byte[] array = new byte[65];
		for (byte b = 0; b < 6; b++)
		{
			array = new byte[65];
			for (byte b2 = 0; b2 < 21; b2++)
			{
				array[0] = 0;
				array[1] = 0;
				int num = 5 - b;
				int num2 = b2 + num * 21;
				if (m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_101 || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_102)
				{
					RGB_S rGB_S2 = WKDColor.cheatRGB_2ndME(colorBuffer[num2].R, colorBuffer[num2].G, colorBuffer[num2].B);
					if (NightMode == 4)
					{
						double num3 = Convert.ToDouble(UserModeLight) / 50.0;
						array[2 + b2] = (byte)((rGB_S2.B == 0) ? ((double)(rGB_S2.B + rGB_S.B)) : ((double)(int)rGB_S2.B * num3));
						array[23 + b2] = (byte)((rGB_S2.G == 0) ? ((double)(rGB_S2.G + rGB_S.G)) : ((double)(int)rGB_S2.G * num3));
						array[44 + b2] = (byte)((rGB_S2.R == 0) ? ((double)(rGB_S2.R + rGB_S.R)) : ((double)(int)rGB_S2.R * num3));
					}
					else
					{
						array[2 + b2] = rGB_S2.B;
						array[23 + b2] = rGB_S2.G;
						array[44 + b2] = rGB_S2.R;
					}
				}
				else if (m_ITE_KB_Type == RGBKB_Type.FourZone || m_ITE_KB_Type == RGBKB_Type.FourZoneSingleColor)
				{
					RGB_S rGB_S3 = WKDColor.cheatRGB_4Zone(m_Project_ID, colorBuffer[num2].R, colorBuffer[num2].G, colorBuffer[num2].B);
					if (NightMode == 4)
					{
						array[2 + b2] = (byte)((rGB_S3.B == 0) ? (rGB_S3.B + rGB_S.B) : rGB_S3.B);
						array[23 + b2] = (byte)((rGB_S3.G == 0) ? (rGB_S3.G + rGB_S.G) : rGB_S3.G);
						array[44 + b2] = (byte)((rGB_S3.R == 0) ? (rGB_S3.R + rGB_S.R) : rGB_S3.R);
					}
					else
					{
						array[2 + b2] = rGB_S3.B;
						array[23 + b2] = rGB_S3.G;
						array[44 + b2] = rGB_S3.R;
					}
				}
				else if (MEZone_2p1ndSeries.Contains(m_ITE_KB_Type))
				{
					RGB_S rGB_S4 = WKDColor.cheatRGB_2p1ndME(colorBuffer[num2].R, colorBuffer[num2].G, colorBuffer[num2].B);
					if (NightMode == 4)
					{
						double num4 = Convert.ToDouble(UserModeLight) / 50.0;
						array[2 + b2] = (byte)((rGB_S4.B == 0) ? ((double)(rGB_S4.B + rGB_S.B)) : ((double)(int)rGB_S4.B * num4));
						array[23 + b2] = (byte)((rGB_S4.G == 0) ? ((double)(rGB_S4.G + rGB_S.G)) : ((double)(int)rGB_S4.G * num4));
						array[44 + b2] = (byte)((rGB_S4.R == 0) ? ((double)(rGB_S4.R + rGB_S.R)) : ((double)(int)rGB_S4.R * num4));
					}
					else
					{
						array[2 + b2] = rGB_S4.B;
						array[23 + b2] = rGB_S4.G;
						array[44 + b2] = rGB_S4.R;
					}
				}
				else if (MEZone_2p2ndSeries.Contains(m_ITE_KB_Type))
				{
					RGB_S rGB_S5 = WKDColor.cheatRGB_2p2ndME(colorBuffer[num2].R, colorBuffer[num2].G, colorBuffer[num2].B);
					if (NightMode == 4)
					{
						double num5 = Convert.ToDouble(UserModeLight) / 50.0;
						array[2 + b2] = (byte)((rGB_S5.B == 0) ? ((double)(rGB_S5.B + rGB_S.B)) : ((double)(int)rGB_S5.B * num5));
						array[23 + b2] = (byte)((rGB_S5.G == 0) ? ((double)(rGB_S5.G + rGB_S.G)) : ((double)(int)rGB_S5.G * num5));
						array[44 + b2] = (byte)((rGB_S5.R == 0) ? ((double)(rGB_S5.R + rGB_S.R)) : ((double)(int)rGB_S5.R * num5));
					}
					else
					{
						array[2 + b2] = rGB_S5.B;
						array[23 + b2] = rGB_S5.G;
						array[44 + b2] = rGB_S5.R;
					}
				}
				else
				{
					array[2 + b2] = colorBuffer[num2].B;
					array[23 + b2] = colorBuffer[num2].G;
					array[44 + b2] = colorBuffer[num2].R;
				}
			}
			try
			{
				Light_Lock();
				HID_Set_RowIndex_16H(b);
				Light_Lock();
				Thread.Sleep(1);
				m_HIDDevice.Write(array, 0, array.Length);
			}
			catch (Exception)
			{
				KBuserModeLock = true;
			}
		}
		KBuserModeLock = true;
		sw.Stop();
		return true;
	}

	private bool Set_ITE_Effect_Type_UserMode_Dynamic(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh)
	{
		sw.Restart();
		if (!KBuserModeLock)
		{
			return true;
		}
		KBuserModeLock = false;
		RGB_S rGB_S = APBackgroundColorConverter(NightModeSelectColorIndex);
		if (NightMode == 4 && Convert.ToUInt32(Light) <= 50)
		{
			Light = Convert.ToByte(50);
		}
		if (bRefresh)
		{
			Light_Lock();
			HID_Set_Effect_Type_08H(2, 51, 0, Light, 0, 0, Save);
		}
		byte[] array = new byte[65];
		for (byte b = 0; b < 6; b++)
		{
			array = new byte[65];
			for (byte b2 = 0; b2 < 21; b2++)
			{
				array[0] = 0;
				array[1] = 0;
				int num = 5 - b;
				int num2 = b2 + num * 21;
				if (m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_101 || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_102)
				{
					RGB_S rGB_S2 = WKDColor.cheatRGB_2ndME(colorBuffer[num2].R, colorBuffer[num2].G, colorBuffer[num2].B);
					if (NightMode == 4)
					{
						double num3 = Convert.ToDouble(UserModeLight) / 50.0;
						array[2 + b2] = (byte)((rGB_S2.B == 0) ? ((double)(rGB_S2.B + rGB_S.B)) : ((double)(int)rGB_S2.B * num3));
						array[23 + b2] = (byte)((rGB_S2.G == 0) ? ((double)(rGB_S2.G + rGB_S.G)) : ((double)(int)rGB_S2.G * num3));
						array[44 + b2] = (byte)((rGB_S2.R == 0) ? ((double)(rGB_S2.R + rGB_S.R)) : ((double)(int)rGB_S2.R * num3));
					}
					else
					{
						array[2 + b2] = rGB_S2.B;
						array[23 + b2] = rGB_S2.G;
						array[44 + b2] = rGB_S2.R;
					}
				}
				else if (m_ITE_KB_Type == RGBKB_Type.FourZone || m_ITE_KB_Type == RGBKB_Type.FourZoneSingleColor)
				{
					RGB_S rGB_S3 = WKDColor.cheatRGB_4Zone(m_Project_ID, colorBuffer[num2].R, colorBuffer[num2].G, colorBuffer[num2].B);
					if (NightMode == 4)
					{
						array[2 + b2] = (byte)((rGB_S3.B == 0) ? (rGB_S3.B + rGB_S.B) : rGB_S3.B);
						array[23 + b2] = (byte)((rGB_S3.G == 0) ? (rGB_S3.G + rGB_S.G) : rGB_S3.G);
						array[44 + b2] = (byte)((rGB_S3.R == 0) ? (rGB_S3.R + rGB_S.R) : rGB_S3.R);
					}
					else
					{
						array[2 + b2] = rGB_S3.B;
						array[23 + b2] = rGB_S3.G;
						array[44 + b2] = rGB_S3.R;
					}
				}
				else if (MEZone_2p1ndSeries.Contains(m_ITE_KB_Type))
				{
					RGB_S rGB_S4 = WKDColor.cheatRGB_2p1ndME(colorBuffer[num2].R, colorBuffer[num2].G, colorBuffer[num2].B);
					if (NightMode == 4)
					{
						double num4 = Convert.ToDouble(UserModeLight) / 50.0;
						array[2 + b2] = (byte)((rGB_S4.B == 0) ? ((double)(rGB_S4.B + rGB_S.B)) : ((double)(int)rGB_S4.B * num4));
						array[23 + b2] = (byte)((rGB_S4.G == 0) ? ((double)(rGB_S4.G + rGB_S.G)) : ((double)(int)rGB_S4.G * num4));
						array[44 + b2] = (byte)((rGB_S4.R == 0) ? ((double)(rGB_S4.R + rGB_S.R)) : ((double)(int)rGB_S4.R * num4));
					}
					else
					{
						array[2 + b2] = rGB_S4.B;
						array[23 + b2] = rGB_S4.G;
						array[44 + b2] = rGB_S4.R;
					}
				}
				else if (MEZone_2p2ndSeries.Contains(m_ITE_KB_Type))
				{
					RGB_S rGB_S5 = WKDColor.cheatRGB_2p2ndME(colorBuffer[num2].R, colorBuffer[num2].G, colorBuffer[num2].B);
					if (NightMode == 4)
					{
						double num5 = Convert.ToDouble(UserModeLight) / 50.0;
						array[2 + b2] = (byte)((rGB_S5.B == 0) ? ((double)(rGB_S5.B + rGB_S.B)) : ((double)(int)rGB_S5.B * num5));
						array[23 + b2] = (byte)((rGB_S5.G == 0) ? ((double)(rGB_S5.G + rGB_S.G)) : ((double)(int)rGB_S5.G * num5));
						array[44 + b2] = (byte)((rGB_S5.R == 0) ? ((double)(rGB_S5.R + rGB_S.R)) : ((double)(int)rGB_S5.R * num5));
					}
					else
					{
						array[2 + b2] = rGB_S5.B;
						array[23 + b2] = rGB_S5.G;
						array[44 + b2] = rGB_S5.R;
					}
				}
				else
				{
					array[2 + b2] = colorBuffer[num2].B;
					array[23 + b2] = colorBuffer[num2].G;
					array[44 + b2] = colorBuffer[num2].R;
				}
			}
			try
			{
				if (CheckKBBufferPlan(b, array))
				{
					HID_Set_RowIndex_26H(b);
					m_HIDDevice.Write(array, 0, array.Length);
				}
			}
			catch (Exception)
			{
				KBuserModeLock = true;
			}
		}
		KBuserModeLock = true;
		int num6 = 30 - Convert.ToInt32(sw.ElapsedMilliseconds);
		Thread.Sleep((num6 > 0) ? num6 : 30);
		sw.Stop();
		return true;
	}

	private bool Set_ITE_Effect_Type_StaticMode(byte Light, byte Save, RGB_S[] colorBuffer, bool bRefresh)
	{
		Log.s(LOG_LEVEL.TRACE, $"RGBKeyboard_ITE | Set_ITE_Effect_Type_StaticMode light ={Light}");
		if (bRefresh)
		{
			Light_Lock();
			HID_Set_Effect_Type_08H(2, 51, 0, Light, 0, 0, Save);
		}
		byte[] array = new byte[65];
		array[0] = 0;
		RGB_S rGB_S = default(RGB_S);
		if (m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_101 || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_102)
		{
			rGB_S = WKDColor.cheatRGB_2ndME(colorBuffer[0].R, colorBuffer[0].G, colorBuffer[0].B);
		}
		else if (MEZone_2p1ndSeries.Contains(m_ITE_KB_Type))
		{
			rGB_S = WKDColor.cheatRGB_2p1ndME(colorBuffer[0].R, colorBuffer[0].G, colorBuffer[0].B);
		}
		else if (MEZone_2p2ndSeries.Contains(m_ITE_KB_Type))
		{
			rGB_S = WKDColor.cheatRGB_2p2ndME(colorBuffer[0].R, colorBuffer[0].G, colorBuffer[0].B);
		}
		else if (m_ITE_KB_Type == RGBKB_Type.FourZone || m_ITE_KB_Type == RGBKB_Type.FourZoneSingleColor)
		{
			rGB_S = WKDColor.cheatRGB_4Zone(m_Project_ID, colorBuffer[0].R, colorBuffer[0].G, colorBuffer[0].B);
		}
		else if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar)
		{
			rGB_S = WKDColor.cheatRGB_HIDLightbar(colorBuffer[0].R, colorBuffer[0].G, colorBuffer[0].B);
		}
		else if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar2)
		{
			rGB_S = WKDColor.cheatRGB_HIDLightbar2(colorBuffer[0].R, colorBuffer[0].G, colorBuffer[0].B);
		}
		for (byte b = 1; b < 65; b += 4)
		{
			array[b] = 0;
			array[b + 1] = rGB_S.R;
			array[b + 2] = rGB_S.G;
			array[b + 3] = rGB_S.B;
		}
		Light_Lock();
		HID_Set_Picture_12H(Save);
		for (byte b2 = 0; b2 < 8; b2++)
		{
			Light_Lock();
			m_HIDDevice.Write(array, 0, array.Length);
			Thread.Sleep(1);
		}
		return true;
	}

	private bool Set_ITE_Effect_Type_FwMode(byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color)
	{
		Log.s(LOG_LEVEL.TRACE, $"RGBKeyboard_ITE | Set_ITE_Effect_Type_FwMode effect={effect} light ={light}");
		byte b = 0;
		if (layout_color.ColorBlocks == 0)
		{
			b = 0;
		}
		else if (layout_color.ColorBlocks != 0 && layout_color.isCircular)
		{
			b = 8;
			for (uint num = 0u; num < layout_color.ColorBlocks; num++)
			{
				HID_Set_Color_14H((byte)(num + 1), layout_color.ColorBuffer[num].R, layout_color.ColorBuffer[num].G, layout_color.ColorBuffer[num].B);
				Thread.Sleep(1);
			}
		}
		else
		{
			b = 1;
			byte r = layout_color.ColorBuffer[0].R;
			byte g = layout_color.ColorBuffer[0].G;
			byte b2 = layout_color.ColorBuffer[0].B;
			HID_Set_Color_14H(b, r, g, b2);
		}
		return HID_Set_Effect_Type_08H(2, effect, speed, light, b, direction, save);
	}

	private bool Set_ITE_Effect_Type_ApMode(byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color)
	{
		m_ap_effect_data.save_effect = effect;
		m_ap_effect_data.save_light = light;
		m_ap_effect_data.save_speed = speed;
		m_ap_effect_data.save_direction = direction;
		m_ap_effect_data.save_layout_color = layout_color;
		if (m_ap_effect_task == null)
		{
			m_ap_effect_task = new Task(AP_Effect_Task);
		}
		m_ap_effect_task_stop = false;
		if (m_ap_effect_task.Status != TaskStatus.Running)
		{
			m_ap_effect_task.Start();
		}
		return true;
	}

	public bool Set_ITE_Effect_Type_ApMode_Stop()
	{
		perKBBuffer = new List<byte[]>
		{
			new byte[0],
			new byte[0],
			new byte[0],
			new byte[0],
			new byte[0],
			new byte[0]
		};
		perLBBuffer = new List<byte[]>
		{
			new byte[0],
			new byte[0],
			new byte[0],
			new byte[0],
			new byte[0],
			new byte[0],
			new byte[0],
			new byte[0]
		};
		m_ap_effect_task_stop = true;
		uint num = 3000u;
		while (m_ap_effect_task != null || num == 0)
		{
			Thread.Sleep(1);
			num--;
		}
		return true;
	}

	public void Save_Lighting_Effect_Data(byte save_effect, byte save_light, byte save_speed, byte save_direction, RGBKB_Color save_layout_color, int save_layout_background, string save_layout_alphabet)
	{
		m_save_lighting_data.bSaved = true;
		m_save_lighting_data.save_effect = save_effect;
		m_save_lighting_data.save_light = save_light;
		m_save_lighting_data.save_speed = save_speed;
		m_save_lighting_data.save_direction = save_direction;
		m_save_lighting_data.save_layout_color = save_layout_color;
		m_save_lighting_data.save_layout_backgroundcolor = save_layout_background;
		m_save_lighting_data.save_layout_alphbet = save_layout_alphabet;
	}

	private void Save_Lighting_Color_Data(RGBKB_Color save_layout_color)
	{
		if (save_layout_color.ColorBlocks < 1)
		{
			return;
		}
		for (int i = 0; i < m_save_lighting_data.save_layout_color.ColorBlocks; i++)
		{
			if (m_save_lighting_data.save_layout_color.ColorBuffer[i].ID == save_layout_color.ColorBuffer[0].ID)
			{
				m_save_lighting_data.save_layout_color.ColorBuffer[i].R = save_layout_color.ColorBuffer[0].R;
				m_save_lighting_data.save_layout_color.ColorBuffer[i].G = save_layout_color.ColorBuffer[0].G;
				m_save_lighting_data.save_layout_color.ColorBuffer[i].B = save_layout_color.ColorBuffer[0].B;
				break;
			}
		}
	}

	public bool Set_Lighting_Effect(byte control, byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color, int layout_backgroundcolor = 0, string layout_alphabet = null)
	{
		NightMode = control;
		NightModeSelectColorIndex = layout_backgroundcolor;
		if (control == 2 || control == 4)
		{
			AlphabetString = layout_alphabet;
		}
		LogCtrl.Write($"RGBKeyboard_ITE | Set_Lighting_Effect effect={effect} light ={light}");
		if (ChangeEffect)
		{
			SingleEffectReset();
			Set_ITE_Effect_Type_ApMode_Stop();
			DLL_SetMusicMode(enable: false, 4, 1, 0);
			BatteryEable(Enable: false);
		}
		if (effect == byte.MaxValue)
		{
			return false;
		}
		if (effect == 34)
		{
			if (m_effect_type == 1 || m_effect_type == 2 || m_effect_type == 4)
			{
				HID_Set_Effect_Type_08H(1, 0, 0, 0, 0, 0, 0);
			}
			RGB_S[] colorBuffer = layout_color.ColorBuffer;
			LogCtrl.Write("Music On");
			DLL_SetMusicMode(enable: true, light, speed, direction, colorBuffer);
		}
		else if (effect == 1)
		{
			SetSingleEffect(effect, light, speed, direction, save, layout_color);
		}
		else if (effect == 51)
		{
			if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar)
			{
				RGB_S[] array = new RGB_S[126];
				array = layout_color.ColorBuffer;
				Set_ITE_Effect_Type_UserMode_Lightbar12h(light, save, array.Take(23).ToArray(), bRefresh: true);
			}
			else if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar2)
			{
				RGB_S[] array2 = new RGB_S[40];
				if (layout_color.ColorBuffer.Count() >= 40)
				{
					for (int i = 0; i < 40; i++)
					{
						array2[i] = layout_color.ColorBuffer[i];
					}
				}
				Set_ITE_Effect_Type_UserMode_Lightbar2(light, save, array2, bRefresh: true, 3);
			}
			else
			{
				RGB_S[] colorBuffer2 = layout_color.ColorBuffer;
				Set_ITE_Effect_Type_UserModeBy12H(light, save, colorBuffer2, bRefresh: true);
			}
		}
		else if (effect == 21)
		{
			if (Ver_High == 18 && Ver_Low >= 9)
			{
				Set_ITE_Effect_Type_FwMode(effect, light, speed, direction, save, layout_color);
			}
			else if (Ver_High == 20 && Ver_Low >= 0)
			{
				Set_ITE_Effect_Type_FwMode(effect, light, speed, direction, save, layout_color);
			}
			else if (Ver_High == 22 && Ver_Low >= 0)
			{
				Set_ITE_Effect_Type_FwMode(effect, light, speed, direction, save, layout_color);
			}
			else
			{
				RGB_S[] colorBuffer3 = layout_color.ColorBuffer;
				SetGamingEffect(light, save, colorBuffer3);
			}
		}
		else if (effect == 35)
		{
			if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar2)
			{
				m_effect_type = 4;
				BatteryEable(Enable: true);
			}
		}
		else if (effect == 13)
		{
			if (MEZone_LightbarSeries.Contains(m_ITE_KB_Type))
			{
				Set_ITE_Effect_Type_FwMode(effect, light, speed, direction, save, layout_color);
			}
			else
			{
				m_effect_type = 4;
				Set_ITE_Effect_Type_ApMode(effect, light, speed, direction, save, layout_color);
			}
		}
		else if (effect == 15 || effect == 12 || effect == 25 || effect == 24 || effect == 23)
		{
			m_effect_type = 4;
			Set_ITE_Effect_Type_ApMode(effect, light, speed, direction, save, layout_color);
		}
		else if (effect == 5 && m_ITE_KB_Type == RGBKB_Type.FourZone)
		{
			HID_Set_Color_14H(1, byte.MaxValue, 0, 0);
			Thread.Sleep(1);
			HID_Set_Color_14H(2, 0, byte.MaxValue, 0);
			Thread.Sleep(1);
			HID_Set_Color_14H(3, 0, 0, byte.MaxValue);
			Thread.Sleep(1);
			HID_Set_Color_14H(4, byte.MaxValue, 0, byte.MaxValue);
			Thread.Sleep(1);
			Set_ITE_Effect_Type_FwMode(effect, light, speed, direction, save, layout_color);
		}
		else
		{
			Set_ITE_Effect_Type_FwMode(effect, light, speed, direction, save, layout_color);
		}
		Enable_EC_OnkeyPressed(effect, direction);
		return true;
	}

	public void SingleEffectReset()
	{
		SingleChangeThread?.Abort();
		SingleChangeThread = null;
	}

	private void ChangeSingleTheme(bool start, byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color)
	{
		if (start && SingleChangeThread == null)
		{
			Task.Run(delegate
			{
				SingleChangeThread = new Thread((ThreadStart)delegate
				{
					int num = 0;
					RGB_S[] colorBuffer = layout_color.ColorBuffer;
					while (start)
					{
						int millisecondsTimeout = Convert.ToInt32(speed) * 1000;
						List<RGB_S> list = new List<RGB_S>();
						for (int i = 0; i < colorBuffer.Length; i++)
						{
							list.Add(colorBuffer[num]);
						}
						RGBKB_Color layout_color2 = new RGBKB_Color
						{
							isCircular = layout_color.isCircular,
							ColorBlocks = layout_color.ColorBlocks,
							ColorBuffer = list.ToArray()
						};
						if (_asyncSingleBrightness != light)
						{
							light = _asyncSingleBrightness;
						}
						SetSingleEffect(effect, light, speed, direction, save, layout_color2);
						Thread.Sleep(millisecondsTimeout);
						num++;
						num %= 7;
					}
				});
				SingleChangeThread.Start();
			});
		}
		else
		{
			SingleEffectReset();
		}
	}

	private void SetSingleEffect(byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color)
	{
		if (Ver_High == 18 && Ver_Low >= 9)
		{
			Set_ITE_Effect_Type_FwMode(effect, light, speed, direction, save, layout_color);
		}
		else if (Ver_High == 20 && Ver_Low >= 0)
		{
			Set_ITE_Effect_Type_FwMode(effect, light, speed, direction, save, layout_color);
		}
		else if (Ver_High == 22 && Ver_Low >= 0)
		{
			Set_ITE_Effect_Type_FwMode(effect, light, speed, direction, save, layout_color);
		}
		else if (m_ITE_KB_Type == RGBKB_Type.FourZone || m_ITE_KB_Type == RGBKB_Type.FourZoneSingleColor)
		{
			m_effect_type = 0;
			Set_ITE_Effect_Type_FwMode(effect, light, speed, direction, save, layout_color);
		}
		else if (MEZone_LightbarSeries.Contains(m_ITE_KB_Type))
		{
			Set_ITE_Effect_Type_FwMode(effect, light, speed, direction, save, layout_color);
		}
		else
		{
			m_effect_type = 2;
			Set_ITE_Effect_Type_StaticMode(light, 0, layout_color.ColorBuffer, bRefresh: true);
		}
	}

	private void SetGamingEffect(byte light, byte save, RGB_S[] colorBuffer)
	{
		RGB_S[] array = new RGB_S[126];
		bool bRefresh = true;
		array[45] = colorBuffer[0];
		array[65] = colorBuffer[1];
		array[66] = colorBuffer[2];
		array[67] = colorBuffer[3];
		array[98] = colorBuffer[0];
		array[118] = colorBuffer[1];
		array[119] = colorBuffer[2];
		array[120] = colorBuffer[3];
		Set_ITE_Effect_Type_UserMode(light, save, array, bRefresh);
	}

	public bool Get_ITE_Light_Value(ref byte light)
	{
		byte Control = 0;
		byte Effect = 0;
		byte Speed = 0;
		byte ColorIndex = 0;
		byte Direction = 0;
		HID_Get_Effect_Type_88H(ref Control, ref Effect, ref Speed, ref light, ref ColorIndex, ref Direction);
		return true;
	}

	private bool Get_LED_Source_Value(ref byte source)
	{
		byte[] buffer = new byte[9] { 0, 162, 0, 0, 0, 0, 0, 0, 0 };
		if (!m_HIDManager.WriteFeature(buffer))
		{
			Log.s(LOG_LEVEL.ERROR, "RGBKeyboard_ITE|TEST_GetLEDSoure : WriteFeature failed");
		}
		else
		{
			Thread.Sleep(1);
			byte[] array = new byte[9];
			if (!m_HIDManager.GetFeature(array))
			{
				Log.s(LOG_LEVEL.ERROR, "RGBKeyboard_ITE|TEST_GetLEDSoure : GetFeature failed");
			}
			else
			{
				source = array[2];
			}
		}
		return true;
	}

	public bool Set_Welcome_TimeOut_Effect_Enable(bool Enable, byte timeoutEffect, byte timeout)
	{
		byte b = (byte)(Enable ? 1u : 0u);
		try
		{
			List<byte> list = new List<byte>();
			list.Add(26);
			list.Add(timeoutEffect);
			list.Add(b);
			list.Add(timeout);
			list.Add(0);
			list.Add(0);
			list.Add(0);
			list.Add(0);
			if (MEZone_LightbarSeries.Contains(m_ITE_KB_Type))
			{
				NvramVariable.SetFwVars("SmartLightbar1A", list.ToArray());
			}
			else
			{
				NvramVariable.SetFwVars("RGBKeyboard1A", list.ToArray());
			}
			HID_Set_TimeOut_1AH(b, timeout, 1);
		}
		catch
		{
		}
		return true;
	}

	public bool Set_Welcome_Effect(byte control, byte effect, byte light, byte speed, byte direction, byte save, RGBKB_Color layout_color)
	{
		if (effect == byte.MaxValue)
		{
			return false;
		}
		if (effect == 1 && (m_ITE_KB_Type == RGBKB_Type.MEZone_1st || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_101 || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_102))
		{
			if (layout_color.ColorBlocks == 0)
			{
				return false;
			}
			uint num = 7u;
			byte r = layout_color.ColorBuffer[0].R;
			byte g = layout_color.ColorBuffer[0].G;
			byte b = layout_color.ColorBuffer[0].B;
			for (uint num2 = 0u; num2 < num; num2++)
			{
				HID_Set_Color_14H((byte)(num2 + 9), r, g, b);
			}
			effect = 3;
		}
		else if (effect == 5 && m_ITE_KB_Type == RGBKB_Type.FourZone)
		{
			HID_Set_Color_14H(9, byte.MaxValue, 0, 0);
			Thread.Sleep(1);
			HID_Set_Color_14H(10, 0, byte.MaxValue, 0);
			Thread.Sleep(1);
			HID_Set_Color_14H(11, 0, 0, byte.MaxValue);
			Thread.Sleep(1);
			HID_Set_Color_14H(12, byte.MaxValue, 0, byte.MaxValue);
			Thread.Sleep(1);
		}
		else
		{
			byte b2 = 0;
			if (layout_color.ColorBlocks == 0)
			{
				b2 = 0;
			}
			else if (layout_color.ColorBlocks != 0 && layout_color.isCircular)
			{
				b2 = 8;
				for (uint num3 = 0u; num3 < layout_color.ColorBlocks; num3++)
				{
					HID_Set_Color_14H((byte)(num3 + 9), layout_color.ColorBuffer[num3].R, layout_color.ColorBuffer[num3].G, layout_color.ColorBuffer[num3].B);
				}
			}
			else
			{
				b2 = 9;
				for (byte b3 = 9; b3 <= 15; b3++)
				{
					HID_Set_Color_14H(b3, layout_color.ColorBuffer[0].R, layout_color.ColorBuffer[0].G, layout_color.ColorBuffer[0].B);
				}
			}
		}
		List<byte> list = new List<byte>();
		list.Add(8);
		list.Add(control);
		list.Add(effect);
		list.Add(speed);
		list.Add(light);
		list.Add(8);
		list.Add(direction);
		list.Add(save);
		if (MEZone_LightbarSeries.Contains(m_ITE_KB_Type))
		{
			NvramVariable.SetFwVars("SmartLightbar08", list.ToArray());
			if (m_save_lighting_data.bSaved)
			{
				Set_Lighting_Effect(2, m_save_lighting_data.save_effect, m_save_lighting_data.save_light, m_save_lighting_data.save_speed, m_save_lighting_data.save_direction, 1, m_save_lighting_data.save_layout_color);
			}
		}
		else
		{
			NvramVariable.SetFwVars("RGBKeyboard08", list.ToArray());
			if (m_save_lighting_data.bSaved)
			{
				Set_Lighting_Effect(2, m_save_lighting_data.save_effect, m_save_lighting_data.save_light, m_save_lighting_data.save_speed, m_save_lighting_data.save_direction, 1, m_save_lighting_data.save_layout_color);
			}
		}
		HID_Set_TimeOut_1AH(1, 4, 1);
		return true;
	}

	private RGBKB_Effect Translate_LM_EffectIndex(byte fw_effect_id)
	{
		return fw_effect_id switch
		{
			1 => RGBKB_Effect.Single, 
			2 => RGBKB_Effect.Breathing, 
			3 => RGBKB_Effect.Wave, 
			5 => RGBKB_Effect.Rainbow, 
			6 => RGBKB_Effect.Ripple, 
			9 => RGBKB_Effect.Marquee, 
			10 => RGBKB_Effect.Raindrop, 
			14 => RGBKB_Effect.Aurora, 
			17 => RGBKB_Effect.Spark, 
			51 => RGBKB_Effect.UserMode, 
			34 => RGBKB_Effect.Music, 
			22 => RGBKB_Effect.RippleO, 
			_ => RGBKB_Effect.UnKnown, 
		};
	}

	private byte Translate_ITE_EffectIndex(RGBKB_Effect layoutEffect)
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
			_ => byte.MaxValue, 
		};
	}

	private byte Translate_ITE_LightValue(uint layoutLight)
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

	private byte Translate_ITE_SpeedValue(uint layoutSpeed)
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

	private byte Translate_ITE_DirectionValue(RGBKB_Direction layoutDirection)
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

	private uint Translate_Layout_LightValue(byte ite_light)
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

	public bool ILM_RGBKB_Init(string IsDefaultTool)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1856, ref Data);
		m_Project_ID = (byte)Convert.ToUInt64(Data);
		m_HIDManager = new HIDManager();
		foreach (ushort pID in PIDList)
		{
			if (!m_HIDManager.Init(1165, pID, 1))
			{
				continue;
			}
			HID_Get_FirmwareVersion_80H(ref Ver_High, ref Ver_Low, ref Ver_Test, ref Ver_Customer);
			switch (m_HIDManager.GetUsagePage())
			{
			case 65298:
				if (m_Project_ID == 17)
				{
					m_ITE_KB_Type = RGBKB_Type.FourZoneSingleColor;
				}
				else
				{
					m_ITE_KB_Type = RGBKB_Type.FourZone;
				}
				break;
			case 65282:
				m_ITE_KB_Type = RGBKB_Type.MEZone_1st;
				break;
			case 65283:
				try
				{
					if (Ver_High == 20)
					{
						byte Data2 = 0;
						EcCtrl.Read(GetType().Name, 1852, ref Data2);
						switch (Convert.ToByte(Data2))
						{
						case 57:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p2nd_97;
							break;
						case 49:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p2nd_98;
							break;
						case 121:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p2nd_99;
							break;
						case 113:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p2nd_100;
							break;
						}
					}
					else if (Ver_High == 19 || Ver_High == 22)
					{
						byte Data3 = 0;
						EcCtrl.Read(GetType().Name, 1852, ref Data3);
						switch (Convert.ToByte(Data3))
						{
						case 25:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p1nd_85;
							break;
						case 17:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p1nd_86;
							break;
						case 73:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p1nd_87;
							break;
						case 65:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p1nd_88;
							break;
						}
					}
					else if (Ver_High == 18)
					{
						byte Data4 = 0;
						EcCtrl.Read(GetType().Name, 1852, ref Data4);
						switch (Convert.ToByte(Data4))
						{
						case 25:
						case 41:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2nd_101;
							break;
						case 17:
						case 33:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2nd_102;
							break;
						default:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2nd_101;
							break;
						}
					}
				}
				catch
				{
					m_ITE_KB_Type = RGBKB_Type.MEZone_2nd_101;
					Log.s(LOG_LEVEL.ERROR, "RGBKeyboard_ITE|ILM_RGBKB_Init : USAGE_PAGE_ME_2ND, query KBID failed");
				}
				break;
			default:
				return false;
			}
			m_HIDDevice = new FileStream(new SafeFileHandle(m_HIDManager.m_Handle, ownsHandle: false), FileAccess.ReadWrite, 65, isAsync: true);
			return true;
		}
		return false;
	}

	public bool ILM_RGBKB_Init()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1856, ref Data);
		m_Project_ID = (byte)Convert.ToUInt64(Data);
		m_HIDManager = new HIDManager();
		foreach (ushort pID in PIDList)
		{
			LogCtrl.Write("Pid : " + pID + " USAGE" + (ushort)1 + DateTime.Now.ToString());
			if (!m_HIDManager.Init(1165, pID, 1))
			{
				continue;
			}
			HID_Get_FirmwareVersion_80H(ref Ver_High, ref Ver_Low, ref Ver_Test, ref Ver_Customer);
			ushort usagePage = m_HIDManager.GetUsagePage();
			LogCtrl.Write("ConfirmStart : Pid : " + pID + "|Page : " + usagePage + " " + DateTime.Now.ToString());
			switch (usagePage)
			{
			case 65298:
				if (m_Project_ID == 17)
				{
					m_ITE_KB_Type = RGBKB_Type.FourZoneSingleColor;
				}
				else
				{
					m_ITE_KB_Type = RGBKB_Type.FourZone;
				}
				break;
			case 65282:
				m_ITE_KB_Type = RGBKB_Type.MEZone_1st;
				break;
			case 65283:
				try
				{
					LogCtrl.Write("ConfirmStart : Ver_High : " + Ver_High);
					if (Ver_High == 19 || Ver_High == 22)
					{
						byte Data2 = 0;
						EcCtrl.Read(GetType().Name, 1852, ref Data2);
						switch (Data2)
						{
						case 25:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p1nd_85;
							break;
						case 17:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p1nd_86;
							break;
						case 73:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p1nd_87;
							break;
						case 65:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p1nd_88;
							break;
						default:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p1nd_85;
							break;
						}
					}
					else if (Ver_High == 18)
					{
						byte Data3 = 0;
						EcCtrl.Read(GetType().Name, 1852, ref Data3);
						switch (Data3)
						{
						case 25:
						case 41:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2nd_101;
							break;
						case 17:
						case 33:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2nd_102;
							break;
						default:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2nd_101;
							break;
						}
					}
					else if (Ver_High == 20)
					{
						byte source = 0;
						Get_LED_Source_Value(ref source);
						WKDColor.SetLEDVenorFromFirmware(source);
						byte Data4 = 0;
						EcCtrl.Read(GetType().Name, 1852, ref Data4);
						switch (Data4)
						{
						case 57:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p2nd_97;
							break;
						case 49:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p2nd_98;
							break;
						case 121:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p2nd_99;
							break;
						case 113:
							m_ITE_KB_Type = RGBKB_Type.MEZone_2p2nd_100;
							break;
						}
					}
					LogCtrl.Write(" KeyboardType  : " + m_ITE_KB_Type);
				}
				catch
				{
					m_ITE_KB_Type = RGBKB_Type.Normal;
					LogCtrl.Write("RGBKeyboard_ITE|ILM_RGBKB_Init : USAGE_PAGE_ME_2ND, query KBID failed");
				}
				break;
			default:
				return false;
			}
			Log.s(LOG_LEVEL.TRACE, " KeyboardType Final : " + m_ITE_KB_Type);
			m_HIDDevice = new FileStream(new SafeFileHandle(m_HIDManager.m_Handle, ownsHandle: false), FileAccess.ReadWrite, 65, isAsync: true);
			return true;
		}
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_Init()
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_Init
		return this.ILM_RGBKB_Init();
	}

	public bool ILM_RGBLB_Init(string DefaultTool)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1856, ref Data);
		m_Project_ID = (byte)Convert.ToUInt64(Data);
		m_HIDManager = new HIDManager();
		foreach (ushort lBPID in LBPIDList)
		{
			if (m_HIDManager.Init(1165, lBPID, 1))
			{
				HID_Get_FirmwareVersion_80H(ref Ver_High, ref Ver_Low, ref Ver_Test, ref Ver_Customer);
				if (m_HIDManager.GetUsagePage() == 65283)
				{
					if (Ver_High == 24)
					{
						m_ITE_KB_Type = RGBKB_Type.MEZone_Lighbar2;
					}
					else
					{
						m_ITE_KB_Type = RGBKB_Type.MEZone_Lighbar;
					}
					m_HIDDevice = new FileStream(new SafeFileHandle(m_HIDManager.m_Handle, ownsHandle: false), FileAccess.ReadWrite, 65, isAsync: true);
					return true;
				}
				return false;
			}
		}
		return false;
	}

	public bool ILM_RGBLB_Init()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1856, ref Data);
		m_Project_ID = (byte)Convert.ToUInt64(Data);
		m_HIDManager = new HIDManager();
		foreach (ushort lBPID in LBPIDList)
		{
			if (m_HIDManager.Init(1165, lBPID, 1))
			{
				HID_Get_FirmwareVersion_80H(ref Ver_High, ref Ver_Low, ref Ver_Test, ref Ver_Customer);
				if (m_HIDManager.GetUsagePage() == 65283)
				{
					if (Ver_High == 24)
					{
						m_ITE_KB_Type = RGBKB_Type.MEZone_Lighbar2;
					}
					else
					{
						m_ITE_KB_Type = RGBKB_Type.MEZone_Lighbar;
					}
					m_HIDDevice = new FileStream(new SafeFileHandle(m_HIDManager.m_Handle, ownsHandle: false), FileAccess.ReadWrite, 65, isAsync: true);
					return true;
				}
				return false;
			}
		}
		return false;
	}

	public void ILM_RGBKB_SetLightingPower(RGBKB_PowerStatus PowerStatus)
	{
		switch (PowerStatus)
		{
		case RGBKB_PowerStatus.Off:
		case RGBKB_PowerStatus.Lighting_off:
			DLL_SetMusicMode(enable: false, 0, 1, 0);
			SingleEffectReset();
			Disable_EC_OnkeyPressed();
			Log.s(LOG_LEVEL.TRACE, "RGBKeyboard_ITE | ILM_RGBKB_SetPower HID_Set_Effect_Type_08H LED_OFF");
			if (m_effect_type == 4)
			{
				Set_ITE_Effect_Type_ApMode_Stop();
			}
			HID_Set_Effect_Type_08H(1, 0, 0, 0, 0, 0, 0);
			break;
		default:
			_ = 3;
			break;
		case RGBKB_PowerStatus.On:
			break;
		}
	}

	public bool ILM_RGBKB_SetPower(RGBKB_PowerStatus PowerStatus)
	{
		if (Monitor.TryEnter(led_off_lock, 2000))
		{
			bool result = true;
			try
			{
				Log.s(LOG_LEVEL.TRACE, $"RGBKeyboard_ITE | ILM_RGBKB_SetPower powerstatus = {PowerStatus}");
				switch (PowerStatus)
				{
				case RGBKB_PowerStatus.Off:
				case RGBKB_PowerStatus.Lighting_off:
					DLL_SetMusicMode(enable: false, 0, 1, 0);
					SingleEffectReset();
					Disable_EC_OnkeyPressed();
					BatteryEable(Enable: false);
					Log.s(LOG_LEVEL.TRACE, "RGBKeyboard_ITE | ILM_RGBKB_SetPower HID_Set_Effect_Type_08H LED_OFF");
					if (m_effect_type == 4)
					{
						Set_ITE_Effect_Type_ApMode_Stop();
					}
					HID_Set_Effect_Type_08H(5, 0, 0, 0, 0, 0, 0);
					HID_Set_Effect_Type_08H(1, 0, 0, 0, 0, 0, 0);
					MEZone_LightbarSeries.Contains(m_ITE_KB_Type);
					if (MEZone_2p1ndSeries.Contains(m_ITE_KB_Type))
					{
						HID_Set_Effect_Type_08H(6, 0, 0, 100, 0, 0, 0);
					}
					break;
				case RGBKB_PowerStatus.On:
				case RGBKB_PowerStatus.Lighting_on:
					MEZone_LightbarSeries.Contains(m_ITE_KB_Type);
					if (MEZone_2p1ndSeries.Contains(m_ITE_KB_Type))
					{
						HID_Set_Effect_Type_08H(6, 0, 1, 100, 0, 0, 0);
					}
					if (m_save_lighting_data.bSaved)
					{
						Log.s(LOG_LEVEL.TRACE, $"RGBKeyboard_ITE | ILM_RGBKB_SetPower Set_Lighting_Effect effect={m_save_lighting_data.save_effect} light ={m_save_lighting_data.save_light}");
						if (NightMode == 4)
						{
							HID_Set_Effect_Type_08H(4, 0, 0, 0, 0, 0, 0);
							Set_Lighting_Effect(4, m_save_lighting_data.save_effect, m_save_lighting_data.save_light, m_save_lighting_data.save_speed, m_save_lighting_data.save_direction, 0, m_save_lighting_data.save_layout_color, m_save_lighting_data.save_layout_backgroundcolor, m_save_lighting_data.save_layout_alphbet);
						}
						else
						{
							Set_Lighting_Effect(2, m_save_lighting_data.save_effect, m_save_lighting_data.save_light, m_save_lighting_data.save_speed, m_save_lighting_data.save_direction, 0, m_save_lighting_data.save_layout_color, m_save_lighting_data.save_layout_backgroundcolor, m_save_lighting_data.save_layout_alphbet);
						}
					}
					else
					{
						Log.s(LOG_LEVEL.TRACE, "RGBKeyboard_ITE | ILM_RGBKB_SetPower becuse ITE FW not support keep status, so return false to AP re-set again");
						result = false;
					}
					break;
				}
				m_save_lighting_data.save_power_status = PowerStatus;
				return result;
			}
			catch
			{
				return false;
			}
			finally
			{
				Monitor.Exit(led_off_lock);
			}
		}
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetPower(RGBKB_PowerStatus PowerStatus)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetPower
		return this.ILM_RGBKB_SetPower(PowerStatus);
	}

	public void StopMusicTransfer()
	{
		DLL_SetMusicMode(enable: false, 4, 1, 0);
	}

	public void StartMusicTransfer()
	{
	}

	public bool ILM_RGBKB_GetPower()
	{
		if (!m_save_lighting_data.save_power_status.Equals(RGBKB_PowerStatus.On))
		{
			return false;
		}
		return true;
	}

	bool ILM_RGBKB.ILM_RGBKB_GetPower()
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetPower
		return this.ILM_RGBKB_GetPower();
	}

	public RGBKB_Type ILM_RGBKB_GetRGBKeyboardType()
	{
		return m_ITE_KB_Type;
	}

	RGBKB_Type ILM_RGBKB.ILM_RGBKB_GetRGBKeyboardType()
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetRGBKeyboardType
		return this.ILM_RGBKB_GetRGBKeyboardType();
	}

	public string ILM_RGBKB_GetFirmwareVersion()
	{
		return $"{Ver_High:X}.{Ver_Low:X}.{Ver_Test:X}.{Ver_Customer:X}";
	}

	string ILM_RGBKB.ILM_RGBKB_GetFirmwareVersion()
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetFirmwareVersion
		return this.ILM_RGBKB_GetFirmwareVersion();
	}

	public bool ILM_RGBKB_SetEffectALL(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, uint layout_light, uint layout_speed, RGBKB_Direction layout_direction, RGBKB_Color layout_color, RGBKB_NV_SAVE layout_save, int layout_backgroundcolor = 0, string layout_alphabet = null)
	{
		byte b = 0;
		byte b2 = 0;
		byte b3 = 0;
		byte b4 = 0;
		byte b5 = 0;
		b = Translate_ITE_EffectIndex(layout_effect);
		b2 = Translate_ITE_LightValue(layout_light);
		b3 = Translate_ITE_SpeedValue(layout_speed);
		b4 = Translate_ITE_DirectionValue(layout_direction);
		b5 = (byte)layout_save;
		switch (layout_mode)
		{
		case RGBKB_Mode.Lighting:
			HID_Set_Effect_Type_08H(5, 0, 0, 0, 0, 0, 0);
			Save_Lighting_Effect_Data(b, b2, b3, b4, layout_color, 0, layout_alphabet);
			Set_Lighting_Effect(2, b, b2, b3, b4, b5, layout_color, 0, layout_alphabet);
			break;
		case RGBKB_Mode.Welcome:
			HID_Set_Effect_Type_08H(5, 0, 0, 0, 0, 0, 0);
			Set_Welcome_Effect(3, b, b2, b3, b4, b5, layout_color);
			break;
		case RGBKB_Mode.Night:
		{
			RGB_S rGB_S = BackgroundColorConverter(layout_backgroundcolor);
			HID_Set_Effect_Type_08H(4, 0, rGB_S.R, rGB_S.G, rGB_S.B, 0, 0);
			if (b != byte.MaxValue)
			{
				Save_Lighting_Effect_Data(b, b2, b3, b4, layout_color, layout_backgroundcolor, layout_alphabet);
				Set_Lighting_Effect(4, b, b2, b3, b4, b5, layout_color, layout_backgroundcolor, layout_alphabet);
				break;
			}
			DLL_SetMusicMode(enable: false, 0, 1, 0);
			Disable_EC_OnkeyPressed();
			Log.s(LOG_LEVEL.TRACE, "RGBKeyboard_ITE | ILM_RGBKB_SetPower HID_Set_Effect_Type_08H LED_OFF");
			if (m_effect_type == 4)
			{
				Set_ITE_Effect_Type_ApMode_Stop();
			}
			HID_Set_Effect_Type_08H(1, 0, 0, 0, 0, 0, 0);
			break;
		}
		}
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetEffectALL(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, uint layout_light, uint layout_speed, RGBKB_Direction layout_direction, RGBKB_Color layout_color, RGBKB_NV_SAVE layout_save, int layout_backgroundcolor = 0, string layout_alphabet = null)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetEffectALL
		return this.ILM_RGBKB_SetEffectALL(layout_mode, layout_effect, layout_light, layout_speed, layout_direction, layout_color, layout_save, layout_backgroundcolor, layout_alphabet);
	}

	public bool ILM_RGBKB_GetEffectALL(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect, ref uint layout_light, ref uint layout_speed, ref RGBKB_Direction layout_direction, ref RGBKB_Color layout_color)
	{
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_GetEffectALL(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect, ref uint layout_light, ref uint layout_speed, ref RGBKB_Direction layout_direction, ref RGBKB_Color layout_color)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetEffectALL
		return this.ILM_RGBKB_GetEffectALL(layout_mode, ref layout_effect, ref layout_light, ref layout_speed, ref layout_direction, ref layout_color);
	}

	public bool ILM_RGBKB_SetEffect(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect)
	{
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetEffect(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetEffect
		return this.ILM_RGBKB_SetEffect(layout_mode, layout_effect);
	}

	public bool ILM_RGBKB_GetEffect(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect)
	{
		switch (layout_mode)
		{
		case RGBKB_Mode.Lighting:
			return false;
		case RGBKB_Mode.Welcome:
		{
			string[] array = new string[3] { "OemServiceWinApp.exe", "ledkb", "/getstatus" };
			int lenRead = 512;
			byte[] array2 = new byte[512];
			OemService.Exec(array.Length, array, lenRead, array2);
			byte fw_effect_id = Convert.ToByte($"{(char)array2[6]}{(char)array2[7]}", 16);
			layout_effect = Translate_LM_EffectIndex(fw_effect_id);
			break;
		}
		}
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_GetEffect(RGBKB_Mode layout_mode, ref RGBKB_Effect layout_effect)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetEffect
		return this.ILM_RGBKB_GetEffect(layout_mode, ref layout_effect);
	}

	public bool ILM_RGBKB_SetBrighntess(uint layout_brightness)
	{
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetBrighntess(uint layout_brightness)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetBrighntess
		return this.ILM_RGBKB_SetBrighntess(layout_brightness);
	}

	public bool ILM_RGBKB_GetBrighntess(ref uint layout_brightness)
	{
		byte light = 0;
		if (Get_ITE_Light_Value(ref light))
		{
			layout_brightness = (byte)Translate_Layout_LightValue(light);
			return true;
		}
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_GetBrighntess(ref uint layout_brightness)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_GetBrighntess
		return this.ILM_RGBKB_GetBrighntess(ref layout_brightness);
	}

	public bool ILM_RGBKB_SetSpeed(uint layout_speed)
	{
		return false;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetSpeed(uint layout_speed)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetSpeed
		return this.ILM_RGBKB_SetSpeed(layout_speed);
	}

	public bool ILM_RGBKB_SetColor(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, RGBKB_Color layout_color)
	{
		if (layout_color.ColorBlocks == 0)
		{
			return false;
		}
		if (layout_mode == RGBKB_Mode.Lighting)
		{
			Save_Lighting_Color_Data(layout_color);
			if (layout_effect == RGBKB_Effect.Single)
			{
				if (m_ITE_KB_Type == RGBKB_Type.FourZone || m_ITE_KB_Type == RGBKB_Type.FourZoneSingleColor)
				{
					byte index = (byte)(layout_color.ColorBuffer[0].ID + 1);
					HID_Set_Color_14H(index, layout_color.ColorBuffer[0].R, layout_color.ColorBuffer[0].G, layout_color.ColorBuffer[0].B);
					return true;
				}
				byte[] array = new byte[65];
				array[0] = 0;
				RGB_S rGB_S = default(RGB_S);
				if (m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_101 || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_102)
				{
					rGB_S = WKDColor.cheatRGB_2ndME(layout_color.ColorBuffer[0].R, layout_color.ColorBuffer[0].G, layout_color.ColorBuffer[0].B);
				}
				else if (MEZone_2p1ndSeries.Contains(m_ITE_KB_Type))
				{
					rGB_S = WKDColor.cheatRGB_2p1ndME(layout_color.ColorBuffer[0].R, layout_color.ColorBuffer[0].G, layout_color.ColorBuffer[0].B);
				}
				else if (MEZone_2p2ndSeries.Contains(m_ITE_KB_Type))
				{
					rGB_S = WKDColor.cheatRGB_2p2ndME(layout_color.ColorBuffer[0].R, layout_color.ColorBuffer[0].G, layout_color.ColorBuffer[0].B);
				}
				else if (m_ITE_KB_Type == RGBKB_Type.FourZone || m_ITE_KB_Type == RGBKB_Type.FourZoneSingleColor)
				{
					rGB_S = WKDColor.cheatRGB_4Zone(m_Project_ID, layout_color.ColorBuffer[0].R, layout_color.ColorBuffer[0].G, layout_color.ColorBuffer[0].B);
				}
				else if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar)
				{
					rGB_S = WKDColor.cheatRGB_HIDLightbar(layout_color.ColorBuffer[0].R, layout_color.ColorBuffer[0].G, layout_color.ColorBuffer[0].B);
				}
				else if (m_ITE_KB_Type == RGBKB_Type.MEZone_Lighbar2)
				{
					rGB_S = WKDColor.cheatRGB_HIDLightbar2(layout_color.ColorBuffer[0].R, layout_color.ColorBuffer[0].G, layout_color.ColorBuffer[0].B);
				}
				for (byte b = 1; b < 65; b += 4)
				{
					array[b] = 0;
					if (m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_101 || m_ITE_KB_Type == RGBKB_Type.MEZone_2nd_102 || MEZone_2p1ndSeries.Contains(m_ITE_KB_Type))
					{
						array[b + 1] = rGB_S.R;
						array[b + 2] = rGB_S.G;
						array[b + 3] = rGB_S.B;
					}
					else
					{
						array[b + 1] = layout_color.ColorBuffer[0].R;
						array[b + 2] = layout_color.ColorBuffer[0].G;
						array[b + 3] = layout_color.ColorBuffer[0].B;
					}
				}
				HID_Set_Picture_12H(0);
				for (byte b2 = 0; b2 < 8; b2++)
				{
					m_HIDDevice.Write(array, 0, array.Length);
					Thread.Sleep(1);
				}
				return true;
			}
			byte index2 = (byte)(layout_color.ColorBuffer[0].ID + 1);
			HID_Set_Color_14H(index2, layout_color.ColorBuffer[0].R, layout_color.ColorBuffer[0].G, layout_color.ColorBuffer[0].B);
		}
		else
		{
			_ = 2;
		}
		return true;
	}

	bool ILM_RGBKB.ILM_RGBKB_SetColor(RGBKB_Mode layout_mode, RGBKB_Effect layout_effect, RGBKB_Color layout_color)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SetColor
		return this.ILM_RGBKB_SetColor(layout_mode, layout_effect, layout_color);
	}

	public bool ILM_RGBKB_SaveLightingLevel(uint layout_light)
	{
		byte b = 0;
		b = Translate_ITE_LightValue(layout_light);
		m_save_lighting_data.save_light = b;
		return true;
	}

	bool ILM_RGBKB.ILM_RGBKB_SaveLightingLevel(uint layout_light)
	{
		//ILSpy generated this explicit interface implementation from .override directive in ILM_RGBKB_SaveLightingLevel
		return this.ILM_RGBKB_SaveLightingLevel(layout_light);
	}
}
