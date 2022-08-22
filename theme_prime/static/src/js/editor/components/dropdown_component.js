/** @odoo-module alias=theme_prime.dropdown_component */
import AbstractComponent from '@theme_prime/js/editor/components/abstract_component';
import { registry } from '@web/core/registry';
import { qweb } from 'web.core';

let DropDownComponent = AbstractComponent.extend({
    template: 'theme_prime.dropdown_component',
    xmlDependencies: AbstractComponent.prototype.xmlDependencies.concat(['/theme_prime/static/src/xml/editor/components/dropdown_component.xml']),
    events: {
        'click .dropdown-item': '_onClickOption'
    },

    /**
     * @constructor
     */
    init: function (parent, options) {
        this.uid = _.uniqueId('tp-dropdown-component-');
        this.records = options.records || [];
        this.recordID = options.recordID || [];
        this.buttonClasses = options.buttonClasses || 'btn-primary';
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Object} record
     */
    _getRecordByID: function (recordID) {
        return _.findWhere(this.records, { id: recordID });
    },
    /**
     * @private
     * @returns {Object} record
     */
    _widgetNotifyChanges: function (recordID) {
        this.recordID = recordID;
        this._refreshDropdown();
        this.trigger_up('tp_component_value_changed', {fieldName: this.fieldName, value: this.recordID});
    },
    /**
     * @private
     */
    _refreshDropdown: function () {
        var $placeholder = $(qweb.render('theme_prime.tp_dropdown_placeholder', {record: this._getRecordByID(this.recordID) }));
        var $items = $(qweb.render('theme_prime.dropdown_component_items', {widget:this, record: this._getRecordByID(this.recordID), records: this.records }));
        this.$('.tp-dropdown-placeholder').empty().append($placeholder);
        this.$('.tp-dropdown-menu').empty().append($items);
    },
    /**
     * @private
     */
    ComponentCurrentState: function () {
        return this._getRecordByID(this.recordID);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
    * @private
    */
    _onClickOption: function (ev) {
        this._widgetNotifyChanges($(ev.currentTarget).attr('data-record-id'));
    },
});

registry.category("theme_prime_components").add("DropDownComponent", DropDownComponent);
export default DropDownComponent;