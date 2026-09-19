using LightingModel;

namespace MyControlCenter.MyRgbKeyboard;

internal class AlphabetEffect
{
	private int shift;

	private char _Alphbet = 'A';

	private RGB_S[] _an_color = new RGB_S[126];

	private RGB_S[] _ColorBuffer;

	private uint _setp;

	public AlphabetEffect(char TargetAlphabet, RGB_S[] ColorBuffer, uint step)
	{
		_Alphbet = TargetAlphabet;
		_ColorBuffer = ColorBuffer;
		_setp = step % 7;
	}

	public void SetShift(int ShiftValue)
	{
		shift = ShiftValue;
	}

	public RGB_S[] GetAlphbetEffect()
	{
		ConvertToKeyboardPoision();
		OutlerFixed();
		return _an_color;
	}

	private void OutlerFixed()
	{
		for (int i = 105; i < 123; i++)
		{
			_an_color[i] = default(RGB_S);
		}
	}

	private void ConvertToKeyboardPoision()
	{
		switch (_Alphbet)
		{
		case 'A':
			A_ColorPosition();
			break;
		case 'B':
			B_ColorPosition();
			break;
		case 'C':
			C_ColorPosition();
			break;
		case 'D':
			D_ColorPosition();
			break;
		case 'E':
			E_ColorPosition();
			break;
		case 'F':
			F_ColorPosition();
			break;
		case 'G':
			G_ColorPosition();
			break;
		case 'H':
			H_ColorPosition();
			break;
		case 'I':
			I_ColorPosition();
			break;
		case 'J':
			J_ColorPosition();
			break;
		case 'K':
			K_ColorPosition();
			break;
		case 'L':
			L_ColorPosition();
			break;
		case 'M':
			M_ColorPosition();
			break;
		case 'N':
			N_ColorPosition();
			break;
		case 'O':
			O_ColorPosition();
			break;
		case 'P':
			P_ColorPosition();
			break;
		case 'Q':
			Q_ColorPosition();
			break;
		case 'R':
			R_ColorPosition();
			break;
		case 'S':
			S_ColorPosition();
			break;
		case 'T':
			T_ColorPosition();
			break;
		case 'U':
			U_ColorPosition();
			break;
		case 'V':
			V_ColorPosition();
			break;
		case 'W':
			W_ColorPosition();
			break;
		case 'X':
			X_ColorPosition();
			break;
		case 'Y':
			Y_ColorPosition();
			break;
		case 'Z':
			Z_ColorPosition();
			break;
		case '0':
			_0_ColorPosition();
			break;
		case '1':
		case '2':
		case '3':
		case '4':
		case '5':
		case '6':
		case '7':
		case '8':
		case '9':
		case ':':
		case ';':
		case '<':
		case '=':
		case '>':
		case '?':
		case '@':
			break;
		}
	}

	private void MarkDisplay(RGB_S[] ColorBuffer, uint step)
	{
		_an_color[shift + 16] = _ColorBuffer[_setp];
		_an_color[shift + 17] = _ColorBuffer[_setp];
		_an_color[shift + 37] = _ColorBuffer[_setp];
		_an_color[shift + 36] = _ColorBuffer[_setp];
		_an_color[shift + 57] = _ColorBuffer[_setp];
		_an_color[shift + 59] = _ColorBuffer[_setp];
		_an_color[shift + 60] = _ColorBuffer[_setp];
		_an_color[shift + 79] = _ColorBuffer[_setp];
		_an_color[shift + 80] = _ColorBuffer[_setp];
	}

	private void _0_ColorPosition()
	{
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 5] = _ColorBuffer[_setp];
		_an_color[shift + 6] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 23] = _ColorBuffer[_setp];
		_an_color[shift + 24] = _ColorBuffer[_setp];
		_an_color[shift + 26] = _ColorBuffer[_setp];
		_an_color[shift + 27] = _ColorBuffer[_setp];
		_an_color[shift + 28] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 45] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 47] = _ColorBuffer[_setp];
		_an_color[shift + 48] = _ColorBuffer[_setp];
		_an_color[shift + 49] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 66] = _ColorBuffer[_setp];
		_an_color[shift + 67] = _ColorBuffer[_setp];
		_an_color[shift + 68] = _ColorBuffer[_setp];
		_an_color[shift + 69] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
		_an_color[shift + 89] = _ColorBuffer[_setp];
	}

	private void A_ColorPosition()
	{
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 24] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 45] = _ColorBuffer[_setp];
		_an_color[shift + 47] = _ColorBuffer[_setp];
		_an_color[shift + 66] = _ColorBuffer[_setp];
		_an_color[shift + 67] = _ColorBuffer[_setp];
		_an_color[shift + 68] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
	}

	private void B_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 4] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 45] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 68] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
		_an_color[shift + 89] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
	}

	private void C_ColorPosition()
	{
		for (int i = shift + 3; i <= shift + 5; i++)
		{
			_an_color[i] = _ColorBuffer[_setp];
		}
		_an_color[shift + 23] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		for (int j = shift + 88; j <= shift + 90; j++)
		{
			_an_color[j] = _ColorBuffer[_setp];
		}
	}

	private void D_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 47] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 67] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
	}

	private void E_ColorPosition()
	{
		for (int i = shift + 1; i <= shift + 4; i++)
		{
			_an_color[i] = _ColorBuffer[_setp];
		}
		_an_color[shift + 22] = _ColorBuffer[_setp];
		for (int j = shift + 44; j <= shift + 46; j++)
		{
			_an_color[j] = _ColorBuffer[_setp];
		}
		_an_color[shift + 65] = _ColorBuffer[_setp];
		for (int k = shift + 87; k <= shift + 90; k++)
		{
			_an_color[k] = _ColorBuffer[_setp];
		}
	}

	private void F_ColorPosition()
	{
		for (int i = shift + 1; i <= shift + 4; i++)
		{
			_an_color[i] = _ColorBuffer[_setp];
		}
		_an_color[shift + 22] = _ColorBuffer[_setp];
		for (int j = shift + 44; j <= shift + 46; j++)
		{
			_an_color[j] = _ColorBuffer[_setp];
		}
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
	}

	private void G_ColorPosition()
	{
		for (int i = shift + 3; i <= shift + 5; i++)
		{
			_an_color[i] = _ColorBuffer[_setp];
		}
		_an_color[shift + 23] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 68] = _ColorBuffer[_setp];
		for (int j = shift + 88; j <= shift + 90; j++)
		{
			_an_color[j] = _ColorBuffer[_setp];
		}
		_an_color[shift + 91] = _ColorBuffer[_setp];
	}

	private void H_ColorPosition()
	{
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 6] = _ColorBuffer[_setp];
		_an_color[shift + 23] = _ColorBuffer[_setp];
		_an_color[shift + 27] = _ColorBuffer[_setp];
		for (int i = shift + 45; i <= shift + 48; i++)
		{
			_an_color[i] = _ColorBuffer[_setp];
		}
		_an_color[shift + 66] = _ColorBuffer[_setp];
		_an_color[shift + 69] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
		_an_color[shift + 91] = _ColorBuffer[_setp];
	}

	private void I_ColorPosition()
	{
		for (int i = shift + 2; i <= shift + 4; i++)
		{
			_an_color[i] = _ColorBuffer[_setp];
		}
		_an_color[shift + 24] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 67] = _ColorBuffer[_setp];
		for (int j = shift + 87; j <= shift + 90; j++)
		{
			_an_color[j] = _ColorBuffer[_setp];
		}
	}

	private void J_ColorPosition()
	{
		for (int i = shift + 2; i <= shift + 4; i++)
		{
			_an_color[i] = _ColorBuffer[_setp];
		}
		_an_color[shift + 24] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 67] = _ColorBuffer[_setp];
		for (int j = shift + 87; j <= shift + 89; j++)
		{
			_an_color[j] = _ColorBuffer[_setp];
		}
	}

	private void K_ColorPosition()
	{
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 5] = _ColorBuffer[_setp];
		_an_color[shift + 23] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 45] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 67] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 89] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
	}

	private void L_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		for (int i = shift + 87; i <= shift + 89; i++)
		{
			_an_color[i] = _ColorBuffer[_setp];
		}
	}

	private void M_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 5] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 23] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 26] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 48] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 69] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 91] = _ColorBuffer[_setp];
	}

	private void N_ColorPosition()
	{
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 6] = _ColorBuffer[_setp];
		_an_color[shift + 23] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 27] = _ColorBuffer[_setp];
		_an_color[shift + 45] = _ColorBuffer[_setp];
		_an_color[shift + 47] = _ColorBuffer[_setp];
		_an_color[shift + 49] = _ColorBuffer[_setp];
		_an_color[shift + 66] = _ColorBuffer[_setp];
		_an_color[shift + 68] = _ColorBuffer[_setp];
		_an_color[shift + 70] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
		_an_color[shift + 91] = _ColorBuffer[_setp];
		_an_color[shift + 92] = _ColorBuffer[_setp];
	}

	private void O_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 4] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 47] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 68] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
		_an_color[shift + 89] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
	}

	private void P_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 4] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 45] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
	}

	private void Q_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 4] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 47] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 67] = _ColorBuffer[_setp];
		_an_color[shift + 68] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
		_an_color[shift + 89] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
		_an_color[shift + 91] = _ColorBuffer[_setp];
	}

	private void R_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 4] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 45] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 47] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 68] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
	}

	private void S_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 4] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 45] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 47] = _ColorBuffer[_setp];
		_an_color[shift + 68] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
		_an_color[shift + 89] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
	}

	private void T_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 4] = _ColorBuffer[_setp];
		_an_color[shift + 23] = _ColorBuffer[_setp];
		_an_color[shift + 45] = _ColorBuffer[_setp];
		_an_color[shift + 66] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
	}

	private void U_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 4] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 47] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 68] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
		_an_color[shift + 89] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
	}

	private void V_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 4] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 65] = _ColorBuffer[_setp];
		_an_color[shift + 66] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
	}

	private void W_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 5] = _ColorBuffer[_setp];
		_an_color[shift + 22] = _ColorBuffer[_setp];
		_an_color[shift + 24] = _ColorBuffer[_setp];
		_an_color[shift + 26] = _ColorBuffer[_setp];
		_an_color[shift + 44] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 48] = _ColorBuffer[_setp];
		for (int i = shift + 65; i <= shift + 68; i++)
		{
			_an_color[i] = _ColorBuffer[_setp];
		}
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
		_an_color[shift + 89] = _ColorBuffer[_setp];
	}

	private void X_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 5] = _ColorBuffer[_setp];
		_an_color[shift + 23] = _ColorBuffer[_setp];
		_an_color[shift + 24] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 67] = _ColorBuffer[_setp];
		_an_color[shift + 68] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
	}

	private void Y_ColorPosition()
	{
		_an_color[shift + 1] = _ColorBuffer[_setp];
		_an_color[shift + 4] = _ColorBuffer[_setp];
		_an_color[shift + 23] = _ColorBuffer[_setp];
		_an_color[shift + 24] = _ColorBuffer[_setp];
		_an_color[shift + 45] = _ColorBuffer[_setp];
		_an_color[shift + 66] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
	}

	private void Z_ColorPosition()
	{
		_an_color[shift + 2] = _ColorBuffer[_setp];
		_an_color[shift + 3] = _ColorBuffer[_setp];
		_an_color[shift + 4] = _ColorBuffer[_setp];
		_an_color[shift + 5] = _ColorBuffer[_setp];
		_an_color[shift + 25] = _ColorBuffer[_setp];
		_an_color[shift + 46] = _ColorBuffer[_setp];
		_an_color[shift + 66] = _ColorBuffer[_setp];
		_an_color[shift + 87] = _ColorBuffer[_setp];
		_an_color[shift + 88] = _ColorBuffer[_setp];
		_an_color[shift + 89] = _ColorBuffer[_setp];
		_an_color[shift + 90] = _ColorBuffer[_setp];
	}
}
