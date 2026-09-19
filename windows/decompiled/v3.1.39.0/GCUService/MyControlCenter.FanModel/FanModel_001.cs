using System;
using System.Collections.Generic;
using System.Linq;

namespace MyControlCenter.FanModel;

internal class FanModel_001 : BaseFanModel
{
	private List<float> template = new List<float>();

	private List<float> CPUUMap1;

	private List<float> CPUTMap1;

	public FanModel_001(string modelname, string TargetName, List<ModelType> datas)
		: base(modelname, TargetName, datas)
	{
	}

	public List<float> getOneOfParam()
	{
		return template;
	}

	public override void Run(int lastDuty)
	{
		int num = 100;
		int num2 = 30;
		double num3 = 40.0;
		List<float> list = new List<float>();
		List<float> list2 = new List<float>();
		foreach (ModelType data in Datas)
		{
			list.Add(Convert.ToSingle(data.CPUTemp));
			list2.Add(Convert.ToSingle(data.CPUUsage));
		}
		CaculateIndex.MAP(DataConverter(list2), 3);
		CPUUMap1 = CaculateIndex.MAP(DataConverter(list2), 1);
		List<float> list3 = CaculateIndex.MAP(DataConverter(list), 5);
		CPUTMap1 = CaculateIndex.MAP(DataConverter(list), 1);
		num3 = FindDegredd(CPUTMap1.Last()).Value;
		for (int i = 1; i < position.Count; i++)
		{
			if (list3[i] < CPUTMap1[i] && list3[i] > list3[i - 1])
			{
				num3 -= (double)(1 / position.Count);
			}
			else if (CPUTMap1[i] > list3[i] && list3[i] < list3[i - 1])
			{
				num3 += (double)(1 / position.Count);
			}
			position[i] = Convert.ToInt32(num3);
			if (position[i] >= num)
			{
				position[i] = num;
			}
			else if (position[i] <= num2)
			{
				position[i] = num2;
			}
		}
		CaculateResult();
	}

	public float GetCPUUsage()
	{
		return CPUUMap1.Last();
	}

	public float GetCPUTemp()
	{
		return CPUTMap1.Last();
	}

	private KeyValuePair<int, int> FindDegredd(float temp)
	{
		Dictionary<int, int> dictionary = new Dictionary<int, int>();
		dictionary.Add(50, 30);
		dictionary.Add(57, 35);
		dictionary.Add(62, 40);
		dictionary.Add(67, 50);
		dictionary.Add(72, 60);
		dictionary.Add(77, 70);
		dictionary.Add(80, 80);
		dictionary.Add(82, 90);
		dictionary.Add(84, 100);
		int num = 0;
		KeyValuePair<int, int> result = dictionary.ElementAt(0);
		foreach (KeyValuePair<int, int> item in dictionary.Reverse())
		{
			if (temp > (float)item.Key)
			{
				result = item;
				break;
			}
			num++;
		}
		if (temp > (float)dictionary.Last().Key)
		{
			result = dictionary.Last();
		}
		return result;
	}
}
