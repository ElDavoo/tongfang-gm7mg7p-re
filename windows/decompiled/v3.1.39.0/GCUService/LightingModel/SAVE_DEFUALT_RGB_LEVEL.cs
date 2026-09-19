using System.IO;
using System.Linq;
using System.Xml.Serialization;
using Newtonsoft.Json;

namespace LightingModel;

public struct SAVE_DEFUALT_RGB_LEVEL
{
	public byte R_Level;

	public byte G_Level;

	public byte B_Level;

	public override bool Equals(object obj)
	{
		byte[] objectByte = getObjectByte(this);
		return getObjectByte(obj).SequenceEqual(objectByte);
	}

	private byte[] getObjectByte(object model)
	{
		using MemoryStream memoryStream = new MemoryStream();
		new XmlSerializer(model.GetType()).Serialize(memoryStream, model);
		return memoryStream.ToArray();
	}

	public override int GetHashCode()
	{
		return ((17 * 23 + R_Level.GetHashCode()) * 23 + G_Level.GetHashCode()) * 23 + B_Level.GetHashCode();
	}

	public static bool operator ==(SAVE_DEFUALT_RGB_LEVEL left, SAVE_DEFUALT_RGB_LEVEL right)
	{
		return left.Equals(right);
	}

	public static bool operator !=(SAVE_DEFUALT_RGB_LEVEL left, SAVE_DEFUALT_RGB_LEVEL right)
	{
		return !(left == right);
	}

	public override string ToString()
	{
		return JsonConvert.SerializeObject(this, Formatting.Indented);
	}
}
