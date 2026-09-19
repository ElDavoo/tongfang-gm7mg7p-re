using System;
using System.Collections.Generic;
using System.Linq;

namespace MyControlCenter;

public class CaculateIndex
{
	public static List<float> BBB(List<StockDataType> MarketData, int DayNo)
	{
		List<float> list = new List<float>();
		int num = 0;
		int num2 = 0;
		List<float> list2 = MAP(MarketData, 1);
		List<float> list3 = MAP(MarketData, 1);
		List<float> list4 = MAP(MarketData, 1);
		List<float> list5 = MAP(MarketData, 1);
		list.Add(0f);
		for (num2 = 1; num2 < MarketData.Count; num2++)
		{
			if (MarketData[num2].sng_End < MarketData[num2].sng_Start)
			{
				if (MarketData[num2 - 1].sng_End < MarketData[num2].sng_Start)
				{
					list2[num2] = Math.Max(MarketData[num2].sng_High - MarketData[num2 - 1].sng_End, MarketData[num2].sng_End - MarketData[num2].sng_Low);
				}
				else
				{
					list2[num2] = Math.Max(MarketData[num2].sng_High - MarketData[num2].sng_Start, MarketData[num2].sng_End - MarketData[num2].sng_Low);
				}
			}
			else if (MarketData[num2].sng_End > MarketData[num2].sng_Start)
			{
				if (MarketData[num2 - 1].sng_End > MarketData[num2].sng_Start)
				{
					list2[num2] = MarketData[num2].sng_High - MarketData[num2].sng_Low;
				}
				else
				{
					list2[num2] = Math.Max(MarketData[num2].sng_Start - MarketData[num2 - 1].sng_End, MarketData[num2].sng_High - MarketData[num2].sng_Low);
				}
			}
			else if (MarketData[num2].sng_High - MarketData[num2].sng_End > MarketData[num2].sng_End - MarketData[num2].sng_Low)
			{
				if (MarketData[num2 - 1].sng_End < MarketData[num2].sng_Start)
				{
					list2[num2] = Math.Max(MarketData[num2].sng_High - MarketData[num2 - 1].sng_End, MarketData[num2].sng_End - MarketData[num2].sng_Low);
				}
				else
				{
					list2[num2] = MarketData[num2].sng_High - MarketData[num2].sng_Start;
				}
			}
			else if (MarketData[num2].sng_High - MarketData[num2].sng_End < MarketData[num2].sng_End - MarketData[num2].sng_Low)
			{
				if (MarketData[num2 - 1].sng_End > MarketData[num2].sng_Start)
				{
					list2[num2] = MarketData[num2].sng_High - MarketData[num2].sng_Low;
				}
				else
				{
					list2[num2] = Math.Max(MarketData[num2].sng_Start - MarketData[num2 - 1].sng_End, MarketData[num2].sng_High - MarketData[num2].sng_Low);
				}
			}
			else if (MarketData[num2 - 1].sng_End > MarketData[num2].sng_Start)
			{
				list2[num2] = Math.Max(MarketData[num2].sng_High - MarketData[num2].sng_Start, MarketData[num2].sng_End - MarketData[num2].sng_Low);
			}
			else if (MarketData[num2 - 1].sng_End < MarketData[num2].sng_Start)
			{
				list2[num2] = Math.Max(MarketData[num2].sng_Start - MarketData[num2 - 1].sng_End, MarketData[num2].sng_High - MarketData[num2].sng_Low);
			}
			else
			{
				list2[num2] = MarketData[num2].sng_High - MarketData[num2].sng_Low;
			}
			if (MarketData[num2].sng_End < MarketData[num2].sng_Start)
			{
				if (MarketData[num2 - 1].sng_End > MarketData[num2].sng_Start)
				{
					list3[num2] = Math.Max(MarketData[num2 - 1].sng_End - MarketData[num2].sng_Start, MarketData[num2].sng_High - MarketData[num2].sng_Low);
				}
				else
				{
					list3[num2] = MarketData[num2].sng_High - MarketData[num2].sng_Low;
				}
			}
			else if (MarketData[num2].sng_End > MarketData[num2].sng_Start)
			{
				if (MarketData[num2 - 1].sng_End > MarketData[num2].sng_Start)
				{
					list3[num2] = Math.Max(MarketData[num2 - 1].sng_End - MarketData[num2].sng_Low, MarketData[num2].sng_High - MarketData[num2].sng_End);
				}
				else
				{
					list3[num2] = Math.Max(MarketData[num2].sng_Start - MarketData[num2].sng_Low, MarketData[num2].sng_High - MarketData[num2].sng_End);
				}
			}
			else if (MarketData[num2].sng_High - MarketData[num2].sng_End > MarketData[num2].sng_End - MarketData[num2].sng_Low)
			{
				if (MarketData[num2 - 1].sng_End > MarketData[num2].sng_Start)
				{
					list3[num2] = Math.Max(MarketData[num2 - 1].sng_End - MarketData[num2].sng_Start, MarketData[num2].sng_High - MarketData[num2].sng_Low);
				}
				else
				{
					list3[num2] = MarketData[num2].sng_High - MarketData[num2].sng_Low;
				}
			}
			else if (MarketData[num2].sng_High - MarketData[num2].sng_End < MarketData[num2].sng_End - MarketData[num2].sng_Low)
			{
				if (MarketData[num2 - 1].sng_End > MarketData[num2].sng_Start)
				{
					list3[num2] = Math.Max(MarketData[num2 - 1].sng_End - MarketData[num2].sng_Low, MarketData[num2].sng_High - MarketData[num2].sng_End);
				}
				else
				{
					list3[num2] = MarketData[num2].sng_Start - MarketData[num2].sng_Low;
				}
			}
			else if (MarketData[num2 - 1].sng_End > MarketData[num2].sng_Start)
			{
				list3[num2] = Math.Max(MarketData[num2 - 1].sng_End - MarketData[num2].sng_Start, MarketData[num2].sng_High - MarketData[num2].sng_Low);
			}
			else if (MarketData[num2 - 1].sng_End < MarketData[num2].sng_Start)
			{
				list3[num2] = Math.Max(MarketData[num2].sng_Start - MarketData[num2].sng_Low, MarketData[num2].sng_High - MarketData[num2].sng_End);
			}
			else
			{
				list3[num2] = MarketData[num2].sng_High - MarketData[num2].sng_Low;
			}
			list4[num2] = list2[num2] - list3[num2];
		}
		list5[0] = 0f;
		for (num = 1; num < MarketData.Count; num++)
		{
			list5[num] = (list4[num] - list5[num - 1]) * 2f / (float)(DayNo + 1) + list5[num - 1];
			list.Add(list5[num]);
		}
		return list;
	}

	public static List<float> Bias(List<StockDataType> MarketData, int DayNo)
	{
		List<float> list = new List<float>();
		float num = 0f;
		for (int i = 0; i < MarketData.Count; i++)
		{
			num = 0f;
			if (i < DayNo - 1)
			{
				for (int j = 0; j <= i; j++)
				{
					num += MarketData[j].sng_End;
				}
				num /= Convert.ToSingle(i + 1);
			}
			else
			{
				for (int num2 = i; num2 >= i - DayNo + 1; num2--)
				{
					num += MarketData[num2].sng_End;
				}
				num /= (float)DayNo;
			}
			num = (MarketData[i].sng_End - num) / num * 100f;
			list.Add(num);
		}
		return list;
	}

	public static List<float> CCI(List<StockDataType> MarketData, int DayNo)
	{
		List<float> list = new List<float>();
		int i = 1;
		float num = 0f;
		float num2 = 0f;
		float num3 = 0f;
		float[] array = new float[MarketData.Count];
		list.Add(0f);
		for (; i < MarketData.Count; i++)
		{
			num = 0f;
			num2 = 0f;
			num3 = MarketData[i].sng_High + MarketData[i].sng_Low + MarketData[i].sng_End;
			_ = MarketData[i].sng_High;
			_ = MarketData[i].sng_Low;
			_ = MarketData[i].sng_End;
			if (i < DayNo - 1)
			{
				for (int j = 1; j <= i; j++)
				{
					array[j] = MarketData[j].sng_High + MarketData[j].sng_Low + MarketData[j].sng_End;
					num += array[j];
				}
				num /= Convert.ToSingle(i + 1);
				for (int k = 1; k <= i; k++)
				{
					num2 += Math.Abs(array[k] - num);
				}
				num2 /= Convert.ToSingle(i + 1);
			}
			else
			{
				for (int num4 = i; num4 > i - DayNo; num4--)
				{
					array[num4] = MarketData[num4].sng_High + MarketData[num4].sng_Low + MarketData[num4].sng_End;
					num += array[num4];
				}
				num /= (float)DayNo;
				for (int num5 = i; num5 > i - DayNo; num5--)
				{
					num2 += Math.Abs(array[num5] - num);
				}
				num2 /= (float)DayNo;
			}
			if (0.015 * (double)num2 != 0.0)
			{
				list.Add(Convert.ToSingle(((double)num3 - Math.Round(num, 3)) / (0.014999999664723873 * Math.Round(num2, 5))));
			}
			else
			{
				list.Add(0f);
			}
		}
		return list;
	}

	public static List<float> EMA(List<StockDataType> MarketData, int DayNo)
	{
		List<float> list = new List<float>();
		float num = Convert.ToSingle(2.0 / (double)Convert.ToSingle(DayNo + 1));
		list.Add(MarketData[0].sng_End);
		for (int i = 1; i < MarketData.Count; i++)
		{
			float item = list[i - 1] + (MarketData[i].sng_End - list[i - 1]) * num;
			list.Add(item);
		}
		return list;
	}

	public static List<float> MAP(List<StockDataType> MarketData, int Days)
	{
		List<float> list = new List<float>();
		foreach (StockDataType MarketDatum in MarketData)
		{
			_ = MarketDatum;
			list.Add(0f);
		}
		for (int i = 0; i < MarketData.Count; i++)
		{
			if (i < Days)
			{
				list[i] = MarketData.Take(i + 1).Sum((StockDataType n) => n.sng_End) / (float)(i + 1);
			}
			else
			{
				list[i] = MarketData.Skip(i + 1 - Days).Take(Days).Sum((StockDataType n) => n.sng_End) / (float)Days;
			}
		}
		for (int num = 0; num < list.Count; num++)
		{
			list[num] = Convert.ToSingle(Math.Round(list[num]));
		}
		return list;
	}

	public static List<float> PSY(List<StockDataType> MarketData, int DayNo)
	{
		List<float> list = new List<float>();
		int num = 0;
		int num2 = 0;
		int num3 = 0;
		float num4 = 0f;
		for (num2 = 0; num2 < MarketData.Count; num2++)
		{
			num3 = 0;
			if (num2 < DayNo)
			{
				num4 = 50f;
			}
			else
			{
				for (num = num2; num >= num2 - DayNo + 1; num--)
				{
					if (MarketData[num].sng_End - MarketData[num - 1].sng_End > 0f)
					{
						num3++;
					}
				}
				num4 = Convert.ToSingle(num3) / Convert.ToSingle(DayNo) * 100f;
			}
			list.Add(num4);
		}
		return list;
	}

	public static List<float> ZEMA(List<StockDataType> MarketData, int DayNo)
	{
		List<float> list = new List<float>();
		float num = Convert.ToSingle(2f / Convert.ToSingle(DayNo + 1));
		int num2 = Convert.ToInt32(Convert.ToSingle((DayNo - 1) / 2));
		int num3 = 0;
		list.Add(MarketData.First().sng_End);
		for (int i = 1; i < MarketData.Count; i++)
		{
			num3 = i - num2;
			if (num3 <= 0)
			{
				num3 = 0;
			}
			list.Add(num * (2f * MarketData[i].sng_End - MarketData[num3].sng_End) + (1f - num) * list[i - 1]);
		}
		return list;
	}
}
