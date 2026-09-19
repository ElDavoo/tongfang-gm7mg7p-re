using System;
using System.Collections.Generic;

namespace MyControlCenter.FanModel;

internal class FanModel_002 : BaseFanModel
{
	private List<float> template = new List<float>();

	public FanModel_002(string modelname, string TargetName, List<ModelType> datas)
		: base(modelname, TargetName, datas)
	{
	}

	public List<float> getOneOfParam()
	{
		return template;
	}

	public new void Run()
	{
		List<float> list = new List<float>();
		List<float> list2 = new List<float>();
		foreach (ModelType data in Datas)
		{
			list.Add(Convert.ToSingle(data.CPUTemp));
			list2.Add(Convert.ToSingle(data.CPUUsage));
		}
		List<float> list3 = CaculateIndex.PSY(DataConverter(list), 3);
		List<float> list4 = CaculateIndex.MAP(DataConverter(list2), 3);
		template = list3;
		CaculateIndex.MAP(DataConverter(list), 5);
		List<float> list5 = CaculateIndex.MAP(DataConverter(list), 3);
		for (int i = 1; i < position.Count; i++)
		{
			if (list4[i] > list4[i - 1])
			{
				if (list3[i] > list3[i - 1])
				{
					position[i] = 1;
				}
			}
			else if (list4[i] < list4[i - 1])
			{
				if (list5[i] < list5[i - 1])
				{
					position[i] = -1;
				}
			}
			else
			{
				position[i] = position[i - 1];
			}
		}
		CaculateResult();
	}
}
