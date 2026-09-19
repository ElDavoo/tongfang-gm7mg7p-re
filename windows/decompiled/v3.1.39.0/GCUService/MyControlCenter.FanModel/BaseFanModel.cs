using System;
using System.Collections.Generic;
using System.Linq;

namespace MyControlCenter.FanModel;

internal class BaseFanModel
{
	protected List<double> Target = new List<double>();

	protected List<double> Result = new List<double>();

	protected List<int> position = new List<int>();

	protected List<ModelType> Datas = new List<ModelType>();

	public string ModelName { get; set; }

	public double Total { get; set; }

	public BaseFanModel()
	{
	}

	public BaseFanModel(string modelname, string TargetName, List<ModelType> datas)
	{
		ModelName = modelname;
		Datas = datas;
		foreach (ModelType data in datas)
		{
			_ = data;
			position.Add(0);
		}
		foreach (ModelType data2 in datas)
		{
			Target.Add(data2.CPUTemp);
		}
		foreach (ModelType data3 in datas)
		{
			_ = data3;
			Result.Add(0.0);
		}
	}

	public List<int> GetPosition()
	{
		return position;
	}

	public List<double> GetResult()
	{
		return Result;
	}

	public void setPosition(int index, int value)
	{
		position[index] = value;
	}

	public void setPostionList(List<int> posList)
	{
		position.Clear();
		for (int i = 0; i < posList.Count; i++)
		{
			position.Add((i != 0) ? posList[i] : 0);
		}
	}

	public List<int> getPositionList()
	{
		return position;
	}

	protected List<StockDataType> DataConverter(List<float> rowdata)
	{
		List<StockDataType> list = new List<StockDataType>();
		foreach (float rowdatum in rowdata)
		{
			StockDataType stockDataType = new StockDataType();
			stockDataType.sng_Start = Convert.ToSingle(rowdatum);
			stockDataType.sng_High = Convert.ToSingle(rowdatum);
			stockDataType.sng_Low = Convert.ToSingle(rowdatum);
			stockDataType.sng_End = Convert.ToSingle(rowdatum);
			list.Add(stockDataType);
		}
		return list;
	}

	public virtual void Run(int lasDuty)
	{
	}

	public virtual void Run()
	{
	}

	protected void CaculateResult()
	{
		List<double> list = new List<double>();
		List<double> list2 = new List<double>();
		foreach (double item in Result)
		{
			_ = item;
			list2.Add(0.0);
		}
		list.Add(0.0);
		for (int i = 1; i < Target.Count; i++)
		{
			list.Add((Target[i] - Target[i - 1]) * -1.0);
		}
		for (int j = 1; j < Result.Count; j++)
		{
			list2[j] = (double)position[j - 1] * list[j];
		}
		Total += list2.Last();
		for (int k = 0; k < Result.Count; k++)
		{
			double num = 0.0;
			for (int l = 0; l < k; l++)
			{
				num += list2[l];
			}
			Result[k] = num;
		}
	}

	public virtual void setModelPosition()
	{
	}

	public virtual void setModelPosition(string filePath)
	{
	}
}
