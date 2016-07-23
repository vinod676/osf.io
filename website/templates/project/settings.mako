<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Settings</%def>

##<!-- Show API key settings -->
##<div mod-meta='{
##        "tpl": "util/render_keys.mako",
##        "uri": "${node["api_url"]}keys/",
##        "replace": true,
##        "kwargs": {
##            "route": "${node["url"]}"
##        }
##    }'></div>

<div class="page-header visible-xs">
  <h2 class="text-300">Settings</h2>
</div>

<div class="row project-page">
    <!-- Begin left column -->
    <div class="col-sm-3 affix-parent scrollspy">

        % if 'write' in user['permissions']:

            <div class="panel panel-default osf-affix" data-spy="affix" data-offset-top="0" data-offset-bottom="263"><!-- Begin sidebar -->
                <ul class="nav nav-stacked nav-pills">

                    % if not node['is_registration']:
                        <li><a href="#configureNodeAnchor">${node['node_type'].capitalize()}</a></li>

                        <li><a href="#selectAddonsAnchor">Select Add-ons</a></li>

                        % if addon_enabled_settings:
                            <li><a href="#configureAddonsAnchor">Configure Add-ons</a></li>
                        % endif

                        <li><a href="#configureWikiAnchor">Wiki</a></li>

                        % if 'admin' in user['permissions']:
                            <li><a href="#configureCommentingAnchor">Commenting</a></li>
                        % endif

                        % if enable_institutions:
                            <li><a href="#configureInstitutionAnchor">Project Affiliation / Branding</a></li>
                        % endif

                        <li><a href="#configureNotificationsAnchor">Email Notifications</a></li>

                    % endif

                    % if node['is_registration']:

                        % if (node['is_public'] or node['embargo_end_date']) and 'admin' in user['permissions']:
                            <li><a href="#withdrawRegistrationAnchor">Withdraw Public Registration</a></li>
                        % endif

                    % endif

                </ul>
            </div><!-- End sidebar -->
        % endif

    </div>
    <!-- End left column -->

    <!-- Begin right column -->
    <div class="col-sm-9">

        % if 'write' in user['permissions']:  ## Begin Configure Project

            % if not node['is_registration']:
                <div class="panel panel-default">
                    <span id="configureNodeAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 id="configureNode" class="panel-title">${node['node_type'].capitalize()}</h3>
                    </div>

                    <div id="projectSettings" class="panel-body">
                        <div class="form-group">
                            <label>Category:</label>
                            <select data-bind="options: categoryOptions, optionsValue: 'value', optionsText: 'label', value: selectedCategory"></select>
                        </div>
                        <div class="form-group">
                            <label for="title">Title:</label>
                            <input class="form-control" type="text" maxlength="200" placeholder="Required" data-bind="value: title,
                                                                                                      valueUpdate: 'afterkeydown'">
                            <span class="text-danger" data-bind="validationMessage: title"></span>
                        </div>
                        <div class="form-group">
                            <label for="description">Description:</label>
                            <textarea placeholder="Optional" data-bind="value: description,
                                             valueUpdate: 'afterkeydown'",
                            class="form-control resize-vertical" style="max-width: 100%"></textarea>
                        </div>
                           <button data-bind="click: cancelAll"
                            class="btn btn-default">Cancel</button>
                            <button data-bind="click: updateAll"
                            class="btn btn-success">Save changes</button>
                        <div class="help-block">
                            <span data-bind="css: messageClass, html: message"></span>
                        </div>
                    % if 'admin' in user['permissions']:
                        <hr />
                            <div class="help-block">
                                A project cannot be deleted if it has any components within it.
                                To delete a parent project, you must first delete all child components
                                by visiting their settings pages.
                            </div>
                            <button id="deleteNode" class="btn btn-danger btn-delete-node">Delete ${node['node_type']}</button>
                    % endif
                    </div>
                </div>

            % endif

        % endif  ## End Configure Project

        % if 'write' in user['permissions']:  ## Begin Select Addons

            % if not node['is_registration']:

                <div class="panel panel-default">
                    <span id="selectAddonsAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">Select Add-ons</h3>
                    </div>
                    <div class="panel-body">
                        <form id="selectAddonsForm">

                            % for category in addon_categories:

                                <%
                                    addons = [
                                        addon
                                        for addon in addons_available
                                        if category in addon.categories
                                    ]
                                %>

                                % if addons:
                                    <h3>${category.capitalize()}</h3>

                                    % for addon in addons:
                                        <div>
                                            <label>
                                                <input
                                                    type="checkbox"
                                                    name="${addon.short_name}"
                                                    class="addon-select"
                                                    ${'checked' if addon.short_name in addons_enabled else ''}
                                                    ${'disabled' if (node['is_registration'] or bool(addon.added_mandatory)) else ''}
                                                />
                                                ${addon.full_name}
                                            </label>
                                        </div>
                                    % endfor

                                % endif

                            % endfor

                            <br />

                            <div class="addon-settings-message text-success" style="padding-top: 10px;"></div>

                        </form>

                    </div>
                </div>

                % if addon_enabled_settings:
                    <span id="configureAddonsAnchor" class="anchor"></span>

                    <div id="configureAddons" class="panel panel-default">

                        <div class="panel-heading clearfix">
                            <h3 class="panel-title">Configure Add-ons</h3>
                        </div>
                        <div class="panel-body">

                        % for node_settings_dict in addon_enabled_settings or []:
                            ${render_node_settings(node_settings_dict)}

                                % if not loop.last:
                                    <hr />
                                % endif

                        % endfor

                        </div>
                    </div>

                % endif

            % endif

        % endif  ## End Select Addons

        % if 'write' in user['permissions']:  ## Begin Wiki Config
            % if not node['is_registration']:
                <div class="panel panel-default">
                    <span id="configureWikiAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">Wiki</h3>
                    </div>

                <div class="panel-body">
                    %if wiki:
                        <form id="selectWikiForm">
                            <div>
                                <label>
                                    <input
                                            type="checkbox"
                                            name="${wiki.short_name}"
                                            class="wiki-select"
                                            data-bind="checked: enabled"
                                    />
                                    Enable the wiki in <b>${node['title']}</b>.
                                </label>

                                <div data-bind="visible: enabled()" class="text-success" style="padding-left: 15px">
                                    <p data-bind="text: wikiMessage"></p>
                                </div>
                                <div data-bind="visible: !enabled()" class="text-danger" style="padding-left: 15px">
                                    <p data-bind="text: wikiMessage"></p>
                                </div>
                            </div>
                        </form>
                    %endif

                        % if include_wiki_settings:
                            <h3>Configure</h3>
                            <div style="padding-left: 15px">
                                %if  node['is_public']:
                                    <p class="text">Control who can edit the wiki of <b>${node['title']}</b></p>
                                %else:
                                    <p class="text">Control who can edit your wiki. To allow all OSF users to edit the wiki, <b>${node['title']}</b> must be public.</p>
                                %endif
                            </div>

                            <form id="wikiSettings" class="osf-treebeard-minimal">
                                <div id="wgrid">
                                    <div class="spinner-loading-wrapper">
                                        <div class="logo-spin logo-lg"></div>
                                        <p class="m-t-sm fg-load-message"> Loading wiki settings...  </p>
                                    </div>
                                </div>
                                <div class="help-block" style="padding-left: 15px">
                                    <p id="configureWikiMessage"></p>
                                </div>
                            </form>
                        % else:
                            <p class="text">To allow all OSF users to edit the wiki, <b>${node['title']}</b> must be public and the wiki enabled.</p>
                        %endif
                    </div>
                </div>
            %endif
        %endif ## End Wiki Config

        % if 'admin' in user['permissions']:  ## Begin Configure Commenting

            % if not node['is_registration']:

                <div class="panel panel-default">
                    <span id="configureCommentingAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">Commenting</h3>
                    </div>

                    <div class="panel-body">

                        <form class="form" id="commentSettings">

                            <div class="radio">
                                <label>
                                    <input type="radio" name="commentLevel" value="private" ${'checked' if comments['level'] == 'private' else ''}>
                                    Only contributors can post comments
                                </label>
                            </div>
                            <div class="radio">
                                <label>
                                    <input type="radio" name="commentLevel" value="public" ${'checked' if comments['level'] == 'public' else ''}>
                                    When the ${node['node_type']} is public, any OSF user can post comments
                                </label>
                            </div>

                            <button class="btn btn-success">Save</button>

                            <!-- Flashed Messages -->
                            <div class="help-block">
                                <p id="configureCommentingMessage"></p>
                            </div>
                        </form>

                    </div>

                </div>
                %endif
            % endif  ## End Configure Commenting

        % if not node['is_registration']:
                % if enable_institutions:
                    <div class="panel panel-default scripted" id="institutionSettings">
                    <span id="configureInstitutionAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">Project Affiliation / Branding</h3>
                    </div>
                    <div class="panel-body">
                        <div class="help-block">
                            <!-- ko if: affiliatedInstitutions().length == 0 -->
                            Projects can be affiliated with institutions that have created OSF for Institutions accounts.
                            This allows:
                            <ul>
                               <li>institutional logos to be displayed on public projects</li>
                               <li>public projects to be discoverable on specific institutional landing pages</li>
                               <li>single sign-on to the OSF with institutional credentials</li>
                               <li><a href="http://help.osf.io/m/os4i">FAQ</a></li>
                            </ul>
                            <!-- /ko -->
                        </div>
                        <!-- ko if: affiliatedInstitutions().length > 0 -->
                        <label>Affiliated Institutions: </label>
                        <!-- /ko -->
                        <table class="table">
                            <tbody>
                                <!-- ko foreach: {data: affiliatedInstitutions, as: 'item'} -->
                                <tr>
                                    <td><img class="img-circle" width="50px" height="50px" data-bind="attr: {src: item.logo_path}"></td>
                                    <td><span data-bind="text: item.name"></span></td>
                                    % if 'admin' in user['permissions']:
                                        <td><button data-bind="disable: $parent.loading(),
                                        click: $parent.clearInst"
                                                    class="pull-right btn btn-danger">Remove</button></td>
                                    % endif
                                </tr>
                                <!-- /ko -->

                            </tbody>
                        </table>
                            </br>
                        <!-- ko if: availableInstitutions().length > 0 -->
                        <label>Available Institutions: </label>
                        <table class="table">
                            <tbody>
                                <!-- ko foreach: {data: availableInstitutions, as: 'item'} -->
                                <tr>
                                    <td><img class="img-circle" width="50px" height="50px" data-bind="attr: {src: item.logo_path}"></td>
                                    <td><span data-bind="text: item.name"></span></td>
                                    % if 'admin' in user['permissions']:
                                        <td><button
                                                data-bind="disable: $parent.loading(),
                                                click: $parent.submitInst"
                                                class="pull-right btn btn-success">Add</button></td>
                                    % endif
                                </tr>
                                <!-- /ko -->
                            </tbody>
                        </table>
                        <!-- /ko -->
                    </div>
                </div>
                % endif
        % endif
        % if user['has_read_permissions']:  ## Begin Configure Email Notifications

            % if not node['is_registration']:

                <div class="panel panel-default">
                    <span id="configureNotificationsAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">Email Notifications</h3>
                    </div>
                    <div class="panel-body">
                        <div class="help-block">
                            <p class="text-muted">These notification settings only apply to you. They do NOT affect any other contributor on this project.</p>
                        </div>
                        <form id="notificationSettings" class="osf-treebeard-minimal">
                            <div id="grid">
                                <div class="spinner-loading-wrapper">
                                    <div class="logo-spin logo-lg"></div>
                                    <p class="m-t-sm fg-load-message"> Loading notification settings...  </p>
                                </div>
                            </div>
                            <div class="help-block" style="padding-left: 15px">
                                <p id="configureNotificationsMessage"></p>
                            </div>
                        </form>
                    </div>
                </div>

            %endif

        % endif ## End Configure Email Notifications

        % if 'admin' in user['permissions']:  ## Begin Retract Registration

            % if node['is_registration']:

                % if node['is_public'] or node['is_embargoed']:

                    <div class="panel panel-default">
                        <span id="withdrawRegistrationAnchor" class="anchor"></span>

                        <div class="panel-heading clearfix">
                            <h3 class="panel-title">Withdraw Registration</h3>
                        </div>

                        <div class="panel-body">

                            % if parent_node['exists']:

                                <div class="help-block">
                                  Withdrawing children components of a registration is not allowed. Should you wish to
                                  withdraw this component, please withdraw its parent registration <a href="${web_url_for('node_setting', pid=node['root_id'])}">here</a>.
                                </div>

                            % else:

                                <div class="help-block">
                                    Withdrawing a registration will remove its content from the OSF, but leave basic metadata
                                    behind. The title of a withdrawn registration and its contributor list will remain, as will
                                    justification or explanation of the withdrawal, should you wish to provide it. Withdrawn
                                    registrations will be marked with a <strong>withdrawn</strong> tag.
                                </div>

                                %if not node['is_pending_retraction']:
                                    <a class="btn btn-danger" href="${web_url_for('node_registration_retraction_get', pid=node['id'])}">Withdraw Registration</a>
                                % else:
                                    <p><strong>This registration is already pending withdrawal.</strong></p>
                                %endif

                            % endif

                        </div>
                    </div>

                % endif

            % endif

        % endif  ## End Retract Registration

    </div>
    <!-- End right column -->

</div>



<%def name="render_node_settings(data)">
    <%
       template_name = data['node_settings_template']
       tpl = data['template_lookup'].get_template(template_name).render(**data)
    %>
    ${ tpl | n }
</%def>

% for name, capabilities in addon_capabilities.iteritems():
    <script id="capabilities-${name}" type="text/html">${ capabilities | n }</script>
% endfor

<%def name="stylesheets()">
    ${parent.stylesheets()}

    <link rel="stylesheet" href="/static/css/pages/project-page.css">
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script>
      window.contextVars = window.contextVars || {};
      window.contextVars.node = window.contextVars.node || {};
      window.contextVars.node.description = ${node['description'] | sjson, n };
      window.contextVars.node.nodeType = ${ node['node_type'] | sjson, n };
      window.contextVars.node.institutions = ${ node['institutions'] | sjson, n };
      window.contextVars.nodeCategories = ${ categories | sjson, n };
      window.contextVars.wiki = window.contextVars.wiki || {};
      window.contextVars.wiki.isEnabled = ${wiki.short_name in addons_enabled | sjson, n };
      window.contextVars.currentUser = window.contextVars.currentUser || {};
      window.contextVars.currentUser.institutions = ${ user['institutions'] | sjson, n };
      window.contextVars.analyticsMeta = $.extend(true, {}, window.contextVars.analyticsMeta, {
          pageMeta: {
              title: 'Settings',
              pubic: false,
          },
      });
    </script>

    <script type="text/javascript" src=${"/static/public/js/project-settings-page.js" | webpack_asset}></script>

    % for js_asset in addon_js:
    <script src="${js_asset | webpack_asset}"></script>
    % endfor


</%def>
