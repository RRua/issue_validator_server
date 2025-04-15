package cn.rbc.termuc;

import android.app.*;

import android.widget.*;
import android.view.*;
import java.io.*;
import android.os.*;
import android.view.ViewTreeObserver.*;
import android.view.inputmethod.*;
import java.lang.reflect.*;
import android.content.*;
import android.content.res.*;
import android.util.Log;
import java.util.*;
import org.json.*;
import java.net.*;
import android.net.*;
import cn.rbc.codeeditor.util.*;
import android.preference.*;
import android.content.pm.*;

public class MainActivity extends Activity implements
	ActionBar.OnNavigationListener, OnGlobalLayoutListener,
	AdapterView.OnItemClickListener, AdapterView.OnItemLongClickListener,
	DialogInterface.OnClickListener {
	private StrComp cmp = new StrComp();
    private File root = Environment.getExternalStorageDirectory();
    
    private ArrayAdapter<String> adp, hda;
	private FragmentManager mFmgr;
	private EditFragment lastFrag = null;
	private boolean byhand = true, inited = false;
    private View keys, showlist;
    private File pwd;
    private TextView pwdpth, msgEmpty;
    private LinearLayout subc;
    private TextEditor codeEditor;
	private Menu _appmenu;
	private ActionBar ab;
	private SearchAction mSearchAction;
	private static MainHandler hand;
	public static Lsp lsp;

	private void envInit() {
		pwd = new File(getPreferences(MODE_PRIVATE).getString("pwd", root.getPath()));
		if (lsp==null) {
			hand = new MainHandler(this);
			lsp = new Lsp();
			lsp.start(this, hand);
		} else
			hand.updateActivity(this);
		Settings.getInstance(PreferenceManager.getDefaultSharedPreferences(getApplicationContext()));
	}

	private void showFrag(Fragment frag) {
		if (frag == lastFrag)
			return;
		FragmentTransaction mTans = mFmgr.beginTransaction();
		if (lastFrag != null)
			mTans.hide(lastFrag);
		mTans.show(frag).commit();
		lastFrag = (EditFragment)frag;
		_appmenu.findItem(R.id.run).setEnabled(lastFrag.type<2);
	}

	public boolean onNavigationItemSelected(int p1, long p2) {
		if (byhand)
			showFrag(mFmgr.findFragmentByTag(hda.getItem(p1)));
		return false;
	}

    @Override
    protected void onCreate(Bundle savedInstanceState) {
		envInit();
		if (Settings.mDarkMode)
			setTheme(android.R.style.Theme_Holo);
        super.onCreate(savedInstanceState);
		getWindow().getDecorView().getViewTreeObserver().addOnGlobalLayoutListener(this);
		mFmgr = getFragmentManager();
		hda = new ArrayAdapter<>(new ContextThemeWrapper(getBaseContext(), android.R.style.Theme_Holo), R.layout.header_dropdown_item);
		Resources.Theme rt = getResources().newTheme();
		rt.applyStyle(android.R.style.Theme_Holo, true);
		hda.setDropDownViewTheme(rt);
		ab = getActionBar();
        ab.setListNavigationCallbacks(hda, this);

		setContentView(R.layout.activity_main);
		requestPermissions(new String[]{
			android.Manifest.permission.READ_EXTERNAL_STORAGE,
			android.Manifest.permission.WRITE_EXTERNAL_STORAGE
		}, PackageManager.PERMISSION_GRANTED);
        showlist = findViewById(R.id.show_list);
		keys = findViewById(R.id.keys);
		subc = findViewById(R.id.subcontainer);
		ListView l = findViewById(R.id.file_list);
		View hd = View.inflate(this, R.layout.list_header, null);
		pwdpth = hd.findViewById(R.id.pwd);
		msgEmpty = findViewById(R.id.msg_empty);
		l.addHeaderView(hd);
		adp = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1);
		l.setAdapter(adp);
		l.setOnItemClickListener(this);
		l.setOnItemLongClickListener(this);
		refresh();
		mSearchAction = new SearchAction(this);
    }

    private void refresh() {
		pwdpth.setText(pwd.getPath());
        adp.clear();
        String[] list = this.pwd.list();
        if (list != null) {
            if (!root.equals(this.pwd))
                adp.add("..");
            adp.addAll(list);
            adp.sort(cmp);
            adp.notifyDataSetChanged();
        }
    }

	@Override
	public void onGlobalLayout() {
		try {
			InputMethodManager inputMethodManager = (InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);
			Method declaredMethod = inputMethodManager.getClass().getDeclaredMethod("getInputMethodWindowVisibleHeight", new Class[0]);
			declaredMethod.setAccessible(true);
			if (((Integer)declaredMethod.invoke(inputMethodManager, new Object[0])).intValue() > 0) {
				showlist.setVisibility(View.GONE);
				subc.setVisibility(View.GONE);
				keys.setVisibility(View.VISIBLE);
				return;
			}
			showlist.setVisibility(View.VISIBLE);
			keys.setVisibility(View.GONE);
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	public void onItemClick(AdapterView<?> av, View v, int i, long n) {
		String _it = adp.getItem(i-1);
		if ("..".equals(_it))
			pwd = pwd.getParentFile();
		else {
			pwd = new File(pwd, _it);
			if (pwd.isFile()) {
				_it = pwd.getAbsolutePath();
				int _i = hda.getCount(), _idx = -1;
				if (mFmgr.findFragmentByTag(_it)!=null) {
					for (_i--; -1<_i && !_it.equals(hda.getItem(_i)); _i--);
				} else {
					if (_it.endsWith(".c"))
						_idx = EditFragment.TYPE_C;
					else if (_it.endsWith(".cpp"))
						_idx = EditFragment.TYPE_CPP;
					else if (_it.endsWith(".h"))
						_idx = EditFragment.TYPE_H;
					else if (_it.endsWith(".hpp"))
						_idx = EditFragment.TYPE_HPP;
					else
						_i = -1;
					if (_idx != -1) {
						if (!inited) {
							lsp.initialize();
							inited = true;
						}
						EditFragment ef = new EditFragment(pwd.getPath(), _idx);
						FragmentTransaction mts = mFmgr.beginTransaction()
							.add(R.id.editFrag, ef, _it);
						if (lastFrag!=null)
							mts.hide(lastFrag);
						mts.show(ef)
							.commit();
						lastFrag = ef;
						hda.add(_it);
						byhand = false;
						if (_i==0) {
							getMenuInflater().inflate(R.menu.main, _appmenu);
							ab.setNavigationMode(ActionBar.NAVIGATION_MODE_LIST);
							ab.setDisplayShowTitleEnabled(false);
							msgEmpty.setVisibility(View.GONE);
						}
						_appmenu.findItem(R.id.run).setEnabled(_idx<2);
					}
				}
				if (_i != -1) {
					ab.setSelectedNavigationItem(_i);
					byhand = true;
				}
				pwd = pwd.getParentFile();
				return;
			}
		}
		refresh();
	}

	public boolean onItemLongClick(AdapterView<?> av, View v, final int i, long l) {
		if ("..".equals(adp.getItem(i-1)))
			return true;
		PopupMenu pm = new PopupMenu(MainActivity.this, v);
		Menu _m = pm.getMenu();
		_m.add(R.string.delete).setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener(){
				public boolean onMenuItemClick(MenuItem mi) {
					if (new File(pwd, adp.getItem(i-1)).delete())
						adp.remove(adp.getItem(i-1));
					return true;
				}
			});
		pm.show();
		return true;
	}

    @Override
    public boolean onOptionsItemSelected(MenuItem menuItem) {
        switch (menuItem.getItemId()) {
            case R.id.run:
                try {
                    lastFrag.save();
					lsp.didSave(lastFrag.getFile());
                    Utils.run(this, new StringBuffer(Utils.PREF).append("/usr/bin/bash").toString(), new String[]{"-c",
					new StringBuffer(lastFrag.getC())
					.append(" \"").append(escape(lastFrag.getFile().getAbsolutePath())).append("\" ")
					.append(Settings.mCFlags).append(" -o $TMPDIR/m && $TMPDIR/m && echo -n \"\nPress any key to exit...\" && read").toString()},
					pwd.getPath(), false);
                } catch (IOException e) {
                    e.printStackTrace();
                }
				break;
			case R.id.undo:
                codeEditor.undo();
                break;
            case R.id.redo:
                codeEditor.redo();
                break;
            case R.id.save:
				try {
					lastFrag.save();
					lsp.didSave(lastFrag.getFile());
					toast("已保存");
				} catch(IOException e) {
					e.printStackTrace();
				}
				break;
			case R.id.search:
				startActionMode(mSearchAction);
				break;
			case R.id.close:
				int sd = ab.getSelectedNavigationIndex();
				String _t = hda.getItem(ab.getSelectedNavigationIndex());
				hda.remove(_t);
				FragmentTransaction mTans = mFmgr.beginTransaction();
				mTans.remove(mFmgr.findFragmentByTag(_t));
				int cnt = hda.getCount();
				if (hda.getCount() == 0) {
					ab.setNavigationMode(ActionBar.NAVIGATION_MODE_STANDARD);
					ab.setDisplayShowTitleEnabled(true);
					_appmenu.clear();
					msgEmpty.setVisibility(View.VISIBLE);
				} else {
					if (cnt == sd)
						sd--;
					lastFrag = (EditFragment)mFmgr.findFragmentByTag(hda.getItem(sd));
					mTans.show(lastFrag);
				}
				mTans.commit();
				lsp.didClose(pwd);
				break;
			case R.id.settings:
				Intent it = new Intent(this, SettingsActivity.class);
				startActivity(it);
				break;
        }
        return true;
    }

    public void inputKey(View view) {
        String charSequence = ((TextView) view).getText().toString();
        if ("⇥".equals(charSequence))
            charSequence = "\t";
		codeEditor.selectText(false);
		codeEditor.getText().setTyping(true);
        codeEditor.paste(charSequence);
    }

    @Override
    public boolean onKeyUp(int i, KeyEvent keyEvent) {
        if (i != keyEvent.KEYCODE_BACK || subc.getVisibility() != View.VISIBLE) {
            return super.onKeyUp(i, keyEvent);
        }
        subc.setVisibility(View.GONE);
        return false;
    }

    @Override
    protected void onRestoreInstanceState(Bundle bundle) {
        super.onRestoreInstanceState(bundle);
        pwd = new File(bundle.getString("pwd"));
		int i = 0, j = 0;
		for (Fragment f:getFragmentManager().getFragments()) {
			hda.add(f.getTag());
			if (!f.isHidden()) {
				j = i;
				codeEditor = (TextEditor)f.getView();
			}
			i++;
		}
		if (!hda.isEmpty()) {
			getMenuInflater().inflate(R.menu.main, _appmenu);
			ab.setNavigationMode(ActionBar.NAVIGATION_MODE_LIST);
			ab.setDisplayShowTitleEnabled(false);
			msgEmpty.setVisibility(View.GONE);
			byhand = false;
			ab.setSelectedNavigationItem(j);
			byhand = true;
		}
    }

    @Override
    public void onSaveInstanceState(Bundle bundle) {
        bundle.putString("pwd", pwd.getPath());
        super.onSaveInstanceState(bundle);
    }

	private EditText fname;

	@Override
	public void onClick(DialogInterface p1, int p2) {
		try {
			File f = new File(pwd, fname.getText().toString());
			if (p2 == DialogInterface.BUTTON_POSITIVE)
				f.createNewFile();
			else
				f.mkdir();
			refresh();
		} catch (IOException e) {
			e.printStackTrace();
			toast(e.getMessage());
		}
	}

	@Override
	protected void onResume() {
		super.onResume();
		// Apply Prefs for Edits
		for (Fragment f:mFmgr.getFragments()) {
			TextEditor ed = (TextEditor)f.getView();
			ed.setWordWrap(Settings.mWordWrap);
			ed.setShowNonPrinting(Settings.mWhiteSpace);
		}
	}

    public void createFile(View view) {
        View inflate = View.inflate(this, R.layout.edit, null);
        fname = inflate.findViewById(R.id.file_name);
		new AlertDialog.Builder(this)
		.setTitle("新建")
		.setView(inflate)
		.setPositiveButton("文件", this)
		.setNeutralButton("文件夹", this)
		.setNegativeButton(android.R.string.cancel, null)
		.create().show();
    }

	@Override
	public boolean onPrepareOptionsMenu(Menu menu)
	{
		_appmenu = menu;
		return super.onPrepareOptionsMenu(menu);
	}

    @Override
    protected void onStop() {
        getPreferences(MODE_PRIVATE).edit().putString("pwd", pwd.getPath()).commit();
        super.onStop();
    }

    private String escape(String str) {
        return str.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("\"", "\\\"");
    }

    public void toast(CharSequence charSequence) {
        HelperUtils.show(Toast.makeText(this, charSequence, 0));
    }

    public void showList(View view) {
        subc.setVisibility(View.VISIBLE);
    }

	public void setEditor(TextEditor edit) {
		codeEditor = edit;
	}

	public TextEditor getEditor() {
		return codeEditor;
	}
}
