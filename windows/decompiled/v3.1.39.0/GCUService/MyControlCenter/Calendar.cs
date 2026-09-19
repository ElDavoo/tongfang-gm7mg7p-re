using System;

namespace MyControlCenter;

internal class Calendar
{
	public class ChineseCalendarException : Exception
	{
		public ChineseCalendarException(string msg)
			: base(msg)
		{
		}
	}

	public class ChineseCalendar
	{
		private struct SolarHolidayStruct
		{
			public int Month;

			public int Day;

			public int Recess;

			public string HolidayName;

			public SolarHolidayStruct(int month, int day, int recess, string name)
			{
				Month = month;
				Day = day;
				Recess = recess;
				HolidayName = name;
			}
		}

		private struct LunarHolidayStruct
		{
			public int Month;

			public int Day;

			public int Recess;

			public string HolidayName;

			public LunarHolidayStruct(int month, int day, int recess, string name)
			{
				Month = month;
				Day = day;
				Recess = recess;
				HolidayName = name;
			}
		}

		private struct WeekHolidayStruct
		{
			public int Month;

			public int WeekAtMonth;

			public int WeekDay;

			public string HolidayName;

			public WeekHolidayStruct(int month, int weekAtMonth, int weekDay, string name)
			{
				Month = month;
				WeekAtMonth = weekAtMonth;
				WeekDay = weekDay;
				HolidayName = name;
			}
		}

		private DateTime _date;

		private DateTime _datetime;

		private int _cYear;

		private int _cMonth;

		private int _cDay;

		private bool _cIsLeapMonth;

		private bool _cIsLeapYear;

		private const int MinYear = 1900;

		private const int MaxYear = 2050;

		private static DateTime MinDay = new DateTime(1900, 1, 30);

		private static DateTime MaxDay = new DateTime(2049, 12, 31);

		private const int GanZhiStartYear = 1864;

		private static DateTime GanZhiStartDay = new DateTime(1899, 12, 22);

		private const string HZNum = "零一二三四五六七八九";

		private const int AnimalStartYear = 1900;

		private static DateTime ChineseConstellationReferDay = new DateTime(2007, 9, 13);

		private static int[] LunarDateArray = new int[151]
		{
			19416, 19168, 42352, 21717, 53856, 55632, 91476, 22176, 39632, 21970,
			19168, 42422, 42192, 53840, 119381, 46400, 54944, 44450, 38320, 84343,
			18800, 42160, 46261, 27216, 27968, 109396, 11104, 38256, 21234, 18800,
			25958, 54432, 59984, 28309, 23248, 11104, 100067, 37600, 116951, 51536,
			54432, 120998, 46416, 22176, 107956, 9680, 37584, 53938, 43344, 46423,
			27808, 46416, 86869, 19872, 42416, 83315, 21168, 43432, 59728, 27296,
			44710, 43856, 19296, 43748, 42352, 21088, 62051, 55632, 23383, 22176,
			38608, 19925, 19152, 42192, 54484, 53840, 54616, 46400, 46752, 103846,
			38320, 18864, 43380, 42160, 45690, 27216, 27968, 44870, 43872, 38256,
			19189, 18800, 25776, 29859, 59984, 27480, 21952, 43872, 38613, 37600,
			51552, 55636, 54432, 55888, 30034, 22176, 43959, 9680, 37584, 51893,
			43344, 46240, 47780, 44368, 21977, 19360, 42416, 86390, 21168, 43312,
			31060, 27296, 44368, 23378, 19296, 42726, 42208, 53856, 60005, 54576,
			23200, 30371, 38608, 19415, 19152, 42192, 118966, 53840, 54560, 56645,
			46496, 22224, 21938, 18864, 42359, 42160, 43600, 111189, 27936, 44448,
			84835
		};

		private static string[] _constellationName = new string[12]
		{
			"白羊座", "金牛座", "雙子座", "巨蟹座", "獅子座", "處女座", "天秤座", "天蠍座", "射手座", "摩羯座",
			"水瓶座", "雙魚座"
		};

		private static string[] _lunarHolidayName = new string[24]
		{
			"小寒", "大寒", "立春", "雨水", "驚蟄", "春分", "清明", "穀雨", "立夏", "小滿",
			"芒種", "夏至", "小暑", "大暑", "立秋", "處暑", "白露", "秋分", "寒露", "霜降",
			"立冬", "小雪", "大雪", "冬至"
		};

		private static string[] _chineseConstellationName = new string[28]
		{
			"角木蛟", "亢金龍", "女土蝠", "房日兔", "心月狐", "尾火虎", "箕水豹", "鬥木獬", "牛金牛", "氐土貉",
			"虛日鼠", "危月燕", "室火豬", "壁水獝", "奎木狼", "婁金狗", "胃土彘", "昴日雞", "畢月烏", "觜火猴",
			"參水猿", "井木犴", "鬼金羊", "柳土獐", "星日馬", "張月鹿", "翼火蛇", "軫水蚓"
		};

		private static string[] SolarTerm = new string[24]
		{
			"小寒", "大寒", "立春", "雨水", "驚蟄", "春分", "清明", "穀雨", "立夏", "小滿",
			"芒種", "夏至", "小暑", "大暑", "立秋", "處暑", "白露", "秋分", "寒露", "霜降",
			"立冬", "小雪", "大雪", "冬至"
		};

		private static int[] sTermInfo = new int[24]
		{
			0, 21208, 42467, 63836, 85337, 107014, 128867, 150921, 173149, 195551,
			218072, 240693, 263343, 285989, 308563, 331033, 353350, 375494, 397447, 419210,
			440795, 462224, 483532, 504758
		};

		private static string ganStr = "甲乙丙丁戊己庚辛壬癸";

		private static string zhiStr = "子醜寅卯辰巳午未申酉戌亥";

		private static string animalStr = "鼠牛虎兔龍蛇馬羊猴雞狗豬";

		private static string nStr1 = "日一二三四五六七八九";

		private static string nStr2 = "初十廿卅";

		private static string[] _monthString = new string[13]
		{
			"出錯", "正月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月",
			"十月", "十一月", "臘月"
		};

		private static SolarHolidayStruct[] sHolidayInfo = new SolarHolidayStruct[51]
		{
			new SolarHolidayStruct(1, 1, 1, "元旦"),
			new SolarHolidayStruct(2, 2, 0, "世界溼地日"),
			new SolarHolidayStruct(2, 10, 0, "國際氣象節"),
			new SolarHolidayStruct(2, 14, 0, "情人節"),
			new SolarHolidayStruct(3, 1, 0, "國際海豹日"),
			new SolarHolidayStruct(3, 5, 0, "學雷鋒紀念日"),
			new SolarHolidayStruct(3, 8, 0, "婦女節"),
			new SolarHolidayStruct(3, 12, 0, "植樹節 孫中山逝世紀念日"),
			new SolarHolidayStruct(3, 14, 0, "國際警察日"),
			new SolarHolidayStruct(3, 15, 0, "消費者權益日"),
			new SolarHolidayStruct(3, 17, 0, "中國國醫節 國際航海日"),
			new SolarHolidayStruct(3, 21, 0, "世界森林日 消除種族歧視國際日 世界兒歌日"),
			new SolarHolidayStruct(3, 22, 0, "世界水日"),
			new SolarHolidayStruct(3, 24, 0, "世界防治結核病日"),
			new SolarHolidayStruct(4, 1, 0, "愚人節"),
			new SolarHolidayStruct(4, 7, 0, "世界衛生日"),
			new SolarHolidayStruct(4, 22, 0, "世界地球日"),
			new SolarHolidayStruct(5, 1, 1, "勞動節"),
			new SolarHolidayStruct(5, 2, 1, "勞動節假日"),
			new SolarHolidayStruct(5, 3, 1, "勞動節假日"),
			new SolarHolidayStruct(5, 4, 0, "青年節"),
			new SolarHolidayStruct(5, 8, 0, "世界紅十字日"),
			new SolarHolidayStruct(5, 12, 0, "國際護士節"),
			new SolarHolidayStruct(5, 31, 0, "世界無煙日"),
			new SolarHolidayStruct(6, 1, 0, "國際兒童節"),
			new SolarHolidayStruct(6, 5, 0, "世界環境保護日"),
			new SolarHolidayStruct(6, 26, 0, "國際禁毒日"),
			new SolarHolidayStruct(7, 1, 0, "建黨節 香港迴歸紀念 世界建築日"),
			new SolarHolidayStruct(7, 11, 0, "世界人口日"),
			new SolarHolidayStruct(8, 1, 0, "建軍節"),
			new SolarHolidayStruct(8, 8, 0, "中國男子節 父親節"),
			new SolarHolidayStruct(8, 15, 0, "抗日戰爭勝利紀念"),
			new SolarHolidayStruct(9, 9, 0, "  逝世紀念"),
			new SolarHolidayStruct(9, 10, 0, "教師節"),
			new SolarHolidayStruct(9, 18, 0, "九·一八事變紀念日"),
			new SolarHolidayStruct(9, 20, 0, "國際愛牙日"),
			new SolarHolidayStruct(9, 27, 0, "世界旅遊日"),
			new SolarHolidayStruct(9, 28, 0, "孔子誕辰"),
			new SolarHolidayStruct(10, 1, 1, "國慶節 國際音樂日"),
			new SolarHolidayStruct(10, 2, 1, "國慶節假日"),
			new SolarHolidayStruct(10, 3, 1, "國慶節假日"),
			new SolarHolidayStruct(10, 6, 0, "老人節"),
			new SolarHolidayStruct(10, 24, 0, "聯合國日"),
			new SolarHolidayStruct(11, 10, 0, "世界青年節"),
			new SolarHolidayStruct(11, 12, 0, "孫中山誕辰紀念"),
			new SolarHolidayStruct(12, 1, 0, "世界艾滋病日"),
			new SolarHolidayStruct(12, 3, 0, "世界殘疾人日"),
			new SolarHolidayStruct(12, 20, 0, "澳門迴歸紀念"),
			new SolarHolidayStruct(12, 24, 0, "平安夜"),
			new SolarHolidayStruct(12, 25, 0, "聖誕節"),
			new SolarHolidayStruct(12, 26, 0, " 誕辰紀念")
		};

		private static LunarHolidayStruct[] lHolidayInfo = new LunarHolidayStruct[10]
		{
			new LunarHolidayStruct(1, 1, 1, "春節"),
			new LunarHolidayStruct(1, 15, 0, "元宵節"),
			new LunarHolidayStruct(5, 5, 0, "端午節"),
			new LunarHolidayStruct(7, 7, 0, "七夕情人節"),
			new LunarHolidayStruct(7, 15, 0, "中元節 盂蘭盆節"),
			new LunarHolidayStruct(8, 15, 0, "中秋節"),
			new LunarHolidayStruct(9, 9, 0, "重陽節"),
			new LunarHolidayStruct(12, 8, 0, "臘八節"),
			new LunarHolidayStruct(12, 23, 0, "北方小年(掃房)"),
			new LunarHolidayStruct(12, 24, 0, "南方小年(撣塵)")
		};

		private static WeekHolidayStruct[] wHolidayInfo = new WeekHolidayStruct[8]
		{
			new WeekHolidayStruct(5, 2, 1, "母親節"),
			new WeekHolidayStruct(5, 3, 1, "全國助殘日"),
			new WeekHolidayStruct(6, 3, 1, "父親節"),
			new WeekHolidayStruct(9, 3, 3, "國際和平日"),
			new WeekHolidayStruct(9, 4, 1, "國際聾人節"),
			new WeekHolidayStruct(10, 1, 2, "國際住房日"),
			new WeekHolidayStruct(10, 1, 4, "國際減輕自然災害日"),
			new WeekHolidayStruct(11, 4, 5, "感恩節")
		};

		public string ChineseCalendarHoliday
		{
			get
			{
				string result = "";
				if (!_cIsLeapMonth)
				{
					LunarHolidayStruct[] array = lHolidayInfo;
					for (int i = 0; i < array.Length; i++)
					{
						LunarHolidayStruct lunarHolidayStruct = array[i];
						if (lunarHolidayStruct.Month == _cMonth && lunarHolidayStruct.Day == _cDay)
						{
							result = lunarHolidayStruct.HolidayName;
							break;
						}
					}
					if (_cMonth == 12)
					{
						int chineseMonthDays = GetChineseMonthDays(_cYear, 12);
						if (_cDay == chineseMonthDays)
						{
							result = "除夕";
						}
					}
				}
				return result;
			}
		}

		public string WeekDayHoliday
		{
			get
			{
				string result = "";
				WeekHolidayStruct[] array = wHolidayInfo;
				for (int i = 0; i < array.Length; i++)
				{
					WeekHolidayStruct weekHolidayStruct = array[i];
					if (CompareWeekDayHoliday(_date, weekHolidayStruct.Month, weekHolidayStruct.WeekAtMonth, weekHolidayStruct.WeekDay))
					{
						result = weekHolidayStruct.HolidayName;
						break;
					}
				}
				return result;
			}
		}

		public string DateHoliday
		{
			get
			{
				string result = "";
				SolarHolidayStruct[] array = sHolidayInfo;
				for (int i = 0; i < array.Length; i++)
				{
					SolarHolidayStruct solarHolidayStruct = array[i];
					if (solarHolidayStruct.Month == _date.Month && solarHolidayStruct.Day == _date.Day)
					{
						result = solarHolidayStruct.HolidayName;
						break;
					}
				}
				return result;
			}
		}

		public DateTime Date
		{
			get
			{
				return _date;
			}
			set
			{
				_date = value;
			}
		}

		public DayOfWeek WeekDay => _date.DayOfWeek;

		public string WeekDayStr => _date.DayOfWeek switch
		{
			DayOfWeek.Sunday => "星期日", 
			DayOfWeek.Monday => "星期一", 
			DayOfWeek.Tuesday => "星期二", 
			DayOfWeek.Wednesday => "星期三", 
			DayOfWeek.Thursday => "星期四", 
			DayOfWeek.Friday => "星期五", 
			_ => "星期六", 
		};

		public string DateString => "公元" + _date.ToLongDateString();

		public bool IsLeapYear => DateTime.IsLeapYear(_date.Year);

		public string ChineseConstellation
		{
			get
			{
				int num = 0;
				num = (_date - ChineseConstellationReferDay).Days % 28;
				if (num < 0)
				{
					return _chineseConstellationName[27 + num];
				}
				return _chineseConstellationName[num];
			}
		}

		public string ChineseHour => GetChineseHour(_datetime);

		public bool IsChineseLeapMonth => _cIsLeapMonth;

		public bool IsChineseLeapYear => _cIsLeapYear;

		public int ChineseDay => _cDay;

		public string ChineseDayString => _cDay switch
		{
			0 => "", 
			10 => "初十", 
			20 => "二十", 
			30 => "三十", 
			_ => nStr2[_cDay / 10].ToString() + nStr1[_cDay % 10], 
		};

		public int ChineseMonth => _cMonth;

		public string ChineseMonthString => _monthString[_cMonth];

		public int ChineseYear => _cYear;

		public string ChineseYearString
		{
			get
			{
				string text = "";
				string text2 = _cYear.ToString();
				for (int i = 0; i < 4; i++)
				{
					text += ConvertNumToChineseNum(text2[i]);
				}
				return text + "年";
			}
		}

		public string ChineseDateString
		{
			get
			{
				if (_cIsLeapMonth)
				{
					return "農曆" + ChineseYearString + "閏" + ChineseMonthString + ChineseDayString;
				}
				return "農曆" + ChineseYearString + ChineseMonthString + ChineseDayString;
			}
		}

		public string ChineseTwentyFourDay
		{
			get
			{
				DateTime dateTime = new DateTime(1900, 1, 6, 2, 5, 0);
				string result = "";
				int year = _date.Year;
				for (int i = 1; i <= 24; i++)
				{
					double value = 525948.76 * (double)(year - 1900) + (double)sTermInfo[i - 1];
					if (dateTime.AddMinutes(value).DayOfYear == _date.DayOfYear)
					{
						result = SolarTerm[i - 1];
						break;
					}
				}
				return result;
			}
		}

		public string ChineseTwentyFourPrevDay
		{
			get
			{
				DateTime dateTime = new DateTime(1900, 1, 6, 2, 5, 0);
				string result = "";
				int year = _date.Year;
				for (int num = 24; num >= 1; num--)
				{
					double value = 525948.76 * (double)(year - 1900) + (double)sTermInfo[num - 1];
					DateTime dateTime2 = dateTime.AddMinutes(value);
					if (dateTime2.DayOfYear < _date.DayOfYear)
					{
						result = string.Format("{0}[{1}]", SolarTerm[num - 1], dateTime2.ToString("yyyy-MM-dd"));
						break;
					}
				}
				return result;
			}
		}

		public string ChineseTwentyFourNextDay
		{
			get
			{
				DateTime dateTime = new DateTime(1900, 1, 6, 2, 5, 0);
				string result = "";
				int year = _date.Year;
				for (int i = 1; i <= 24; i++)
				{
					double value = 525948.76 * (double)(year - 1900) + (double)sTermInfo[i - 1];
					DateTime dateTime2 = dateTime.AddMinutes(value);
					if (dateTime2.DayOfYear > _date.DayOfYear)
					{
						result = string.Format("{0}[{1}]", SolarTerm[i - 1], dateTime2.ToString("yyyy-MM-dd"));
						break;
					}
				}
				return result;
			}
		}

		public string Constellation
		{
			get
			{
				int num = 0;
				int year = _date.Year;
				int month = _date.Month;
				int day = _date.Day;
				year = month * 100 + day;
				num = ((year < 321 || year > 419) ? ((year >= 420 && year <= 520) ? 1 : ((year >= 521 && year <= 620) ? 2 : ((year >= 621 && year <= 722) ? 3 : ((year >= 723 && year <= 822) ? 4 : ((year >= 823 && year <= 922) ? 5 : ((year >= 923 && year <= 1022) ? 6 : ((year >= 1023 && year <= 1121) ? 7 : ((year >= 1122 && year <= 1221) ? 8 : ((year >= 1222 || year <= 119) ? 9 : ((year >= 120 && year <= 218) ? 10 : ((year >= 219 && year <= 320) ? 11 : 0))))))))))) : 0);
				return _constellationName[num];
			}
		}

		public int Animal => (_date.Year - 1900) % 12 + 1;

		public string AnimalString
		{
			get
			{
				int num = _date.Year - 1900;
				return animalStr[num % 12].ToString();
			}
		}

		public string GanZhiYearString
		{
			get
			{
				int num = (_cYear - 1864) % 60;
				return ganStr[num % 10].ToString() + zhiStr[num % 12] + "年";
			}
		}

		public string GanZhiMonthString
		{
			get
			{
				int num = ((_cMonth <= 10) ? (_cMonth + 2) : (_cMonth - 10));
				string text = zhiStr[num - 1].ToString();
				int num2 = 1;
				switch ((_cYear - 1864) % 60 % 10)
				{
				case 0:
					num2 = 3;
					break;
				case 1:
					num2 = 5;
					break;
				case 2:
					num2 = 7;
					break;
				case 3:
					num2 = 9;
					break;
				case 4:
					num2 = 1;
					break;
				case 5:
					num2 = 3;
					break;
				case 6:
					num2 = 5;
					break;
				case 7:
					num2 = 7;
					break;
				case 8:
					num2 = 9;
					break;
				case 9:
					num2 = 1;
					break;
				}
				return ganStr[(num2 + _cMonth - 2) % 10] + text + "月";
			}
		}

		public string GanZhiDayString
		{
			get
			{
				int num = (_date - GanZhiStartDay).Days % 60;
				return ganStr[num % 10].ToString() + zhiStr[num % 12] + "日";
			}
		}

		public string GanZhiDateString => GanZhiYearString + GanZhiMonthString + GanZhiDayString;

		public ChineseCalendar(DateTime dt)
		{
			CheckDateLimit(dt);
			_date = dt.Date;
			_datetime = dt;
			int num = 0;
			int num2 = 0;
			int num3 = (_date - MinDay).Days;
			int i;
			for (i = 1900; i <= 2050; i++)
			{
				num2 = GetChineseYearDays(i);
				if (num3 - num2 < 1)
				{
					break;
				}
				num3 -= num2;
			}
			_cYear = i;
			num = GetChineseLeapMonth(_cYear);
			if (num > 0)
			{
				_cIsLeapYear = true;
			}
			else
			{
				_cIsLeapYear = false;
			}
			_cIsLeapMonth = false;
			for (i = 1; i <= 12; i++)
			{
				if (num > 0 && i == num + 1 && !_cIsLeapMonth)
				{
					_cIsLeapMonth = true;
					i--;
					num2 = GetChineseLeapMonthDays(_cYear);
				}
				else
				{
					_cIsLeapMonth = false;
					num2 = GetChineseMonthDays(_cYear, i);
				}
				num3 -= num2;
				if (num3 <= 0)
				{
					break;
				}
			}
			num3 += num2;
			_cMonth = i;
			_cDay = num3;
		}

		public ChineseCalendar(int cy, int cm, int cd, bool leapMonthFlag)
		{
			CheckChineseDateLimit(cy, cm, cd, leapMonthFlag);
			_cYear = cy;
			_cMonth = cm;
			_cDay = cd;
			int num = 0;
			for (int i = 1900; i < cy; i++)
			{
				int chineseYearDays = GetChineseYearDays(i);
				num += chineseYearDays;
			}
			int chineseLeapMonth = GetChineseLeapMonth(cy);
			if (chineseLeapMonth != 0)
			{
				_cIsLeapYear = true;
			}
			else
			{
				_cIsLeapYear = false;
			}
			if (cm != chineseLeapMonth)
			{
				_cIsLeapMonth = false;
			}
			else
			{
				_cIsLeapMonth = leapMonthFlag;
			}
			if (!_cIsLeapYear || cm < chineseLeapMonth)
			{
				for (int i = 1; i < cm; i++)
				{
					int chineseYearDays = GetChineseMonthDays(cy, i);
					num += chineseYearDays;
				}
				if (cd > GetChineseMonthDays(cy, cm))
				{
					throw new ChineseCalendarException("不合法的農曆日期");
				}
				num += cd;
			}
			else
			{
				for (int i = 1; i < cm; i++)
				{
					int chineseYearDays = GetChineseMonthDays(cy, i);
					num += chineseYearDays;
				}
				if (cm > chineseLeapMonth)
				{
					int chineseYearDays = GetChineseLeapMonthDays(cy);
					num += chineseYearDays;
					if (cd > GetChineseMonthDays(cy, cm))
					{
						throw new ChineseCalendarException("不合法的農曆日期");
					}
					num += cd;
				}
				else
				{
					if (_cIsLeapMonth)
					{
						int chineseYearDays = GetChineseMonthDays(cy, cm);
						num += chineseYearDays;
					}
					if (cd > GetChineseLeapMonthDays(cy))
					{
						throw new ChineseCalendarException("不合法的農曆日期");
					}
					num += cd;
				}
			}
			_date = MinDay.AddDays(num);
		}

		private int GetChineseMonthDays(int year, int month)
		{
			if (BitTest32(LunarDateArray[year - 1900] & 0xFFFF, 16 - month))
			{
				return 30;
			}
			return 29;
		}

		private int GetChineseLeapMonth(int year)
		{
			return LunarDateArray[year - 1900] & 0xF;
		}

		private int GetChineseLeapMonthDays(int year)
		{
			if (GetChineseLeapMonth(year) != 0)
			{
				if ((LunarDateArray[year - 1900] & 0x10000) != 0)
				{
					return 30;
				}
				return 29;
			}
			return 0;
		}

		private int GetChineseYearDays(int year)
		{
			int num = 348;
			int num2 = 32768;
			int num3 = LunarDateArray[year - 1900] & 0xFFFF;
			for (int i = 0; i < 12; i++)
			{
				if ((num3 & num2) != 0)
				{
					num++;
				}
				num2 >>= 1;
			}
			return num + GetChineseLeapMonthDays(year);
		}

		private string GetChineseHour(DateTime dt)
		{
			int num = dt.Hour;
			if (dt.Minute != 0)
			{
				num++;
			}
			int num2 = num / 2;
			if (num2 >= 12)
			{
				num2 = 0;
			}
			int num3 = (((_date - GanZhiStartDay).Days % 60 % 10 + 1) * 2 - 1) % 10 - 1;
			return (ganStr.Substring(num3) + ganStr.Substring(0, num3 + 2))[num2].ToString() + zhiStr[num2];
		}

		private void CheckDateLimit(DateTime dt)
		{
			if (dt < MinDay || dt > MaxDay)
			{
				throw new ChineseCalendarException("超出可轉換的日期");
			}
		}

		private void CheckChineseDateLimit(int year, int month, int day, bool leapMonth)
		{
			if (year < 1900 || year > 2050)
			{
				throw new ChineseCalendarException("非法農曆日期");
			}
			if (month < 1 || month > 12)
			{
				throw new ChineseCalendarException("非法農曆日期");
			}
			if (day < 1 || day > 30)
			{
				throw new ChineseCalendarException("非法農曆日期");
			}
			int chineseLeapMonth = GetChineseLeapMonth(year);
			if (leapMonth && month != chineseLeapMonth)
			{
				throw new ChineseCalendarException("非法農曆日期");
			}
		}

		private string ConvertNumToChineseNum(char n)
		{
			if (n < '0' || n > '9')
			{
				return "";
			}
			return n switch
			{
				'0' => "零一二三四五六七八九"[0].ToString(), 
				'1' => "零一二三四五六七八九"[1].ToString(), 
				'2' => "零一二三四五六七八九"[2].ToString(), 
				'3' => "零一二三四五六七八九"[3].ToString(), 
				'4' => "零一二三四五六七八九"[4].ToString(), 
				'5' => "零一二三四五六七八九"[5].ToString(), 
				'6' => "零一二三四五六七八九"[6].ToString(), 
				'7' => "零一二三四五六七八九"[7].ToString(), 
				'8' => "零一二三四五六七八九"[8].ToString(), 
				'9' => "零一二三四五六七八九"[9].ToString(), 
				_ => "", 
			};
		}

		private bool BitTest32(int num, int bitpostion)
		{
			if (bitpostion > 31 || bitpostion < 0)
			{
				throw new Exception("Error Param: bitpostion[0-31]:" + bitpostion);
			}
			int num2 = 1 << bitpostion;
			if ((num & num2) == 0)
			{
				return false;
			}
			return true;
		}

		private int ConvertDayOfWeek(DayOfWeek dayOfWeek)
		{
			return dayOfWeek switch
			{
				DayOfWeek.Sunday => 1, 
				DayOfWeek.Monday => 2, 
				DayOfWeek.Tuesday => 3, 
				DayOfWeek.Wednesday => 4, 
				DayOfWeek.Thursday => 5, 
				DayOfWeek.Friday => 6, 
				DayOfWeek.Saturday => 7, 
				_ => 0, 
			};
		}

		private bool CompareWeekDayHoliday(DateTime date, int month, int week, int day)
		{
			bool result = false;
			if (date.Month == month && ConvertDayOfWeek(date.DayOfWeek) == day)
			{
				DateTime dateTime = new DateTime(date.Year, date.Month, 1);
				int num = ConvertDayOfWeek(dateTime.DayOfWeek);
				int num2 = 7 - ConvertDayOfWeek(dateTime.DayOfWeek) + 1;
				if (num > day)
				{
					if ((week - 1) * 7 + day + num2 == date.Day)
					{
						result = true;
					}
				}
				else if (day + num2 + (week - 2) * 7 == date.Day)
				{
					result = true;
				}
			}
			return result;
		}

		public ChineseCalendar NextDay()
		{
			return new ChineseCalendar(_date.AddDays(1.0));
		}

		public ChineseCalendar PervDay()
		{
			return new ChineseCalendar(_date.AddDays(-1.0));
		}
	}
}
